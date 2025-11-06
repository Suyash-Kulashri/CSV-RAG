"""
Retriever for fetching data from Neo4j and Milvus.
"""
from typing import Dict, List, Optional
import numpy as np
from database.neo4j_client import Neo4jClient
from database.milvus_client import MilvusClient
from utils.embeddings import EmbeddingGenerator


class Retriever:
    """Retrieve data from Neo4j and Milvus based on parsed queries."""
    
    def __init__(self, 
                 neo4j_client: Neo4jClient,
                 milvus_client: Optional[MilvusClient] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize retriever.
        
        Args:
            neo4j_client: Neo4j client instance
            milvus_client: Milvus client instance (optional)
            embedding_generator: Embedding generator for query embeddings (optional)
        """
        self.neo4j = neo4j_client
        self.milvus = milvus_client
        self.embedding_generator = embedding_generator
        
        # Initialize embedding generator if not provided and Milvus is available
        if self.milvus and not self.embedding_generator:
            self.embedding_generator = EmbeddingGenerator()
    
    def retrieve(self, 
                 parsed_query: Dict,
                 top_k: int = 5,
                 similarity_threshold: float = 0.7) -> Dict:
        """
        Retrieve data from both Neo4j and Milvus based on parsed query.
        
        Args:
            parsed_query: Parsed query dictionary from QueryParser
            top_k: Number of top results to retrieve from Milvus
            similarity_threshold: Minimum similarity score for Milvus results
            
        Returns:
            Dictionary with:
            - neo4j_results: Structured data from Neo4j
            - milvus_results: PDF chunks from Milvus (if available)
        """
        results = {
            'neo4j_results': {},
            'milvus_results': []
        }
        
        # Retrieve from Neo4j
        results['neo4j_results'] = self._retrieve_from_neo4j(parsed_query)
        
        # Retrieve from Milvus (only if Milvus is available and query is relevant)
        if self.milvus and self.embedding_generator:
            results['milvus_results'] = self._retrieve_from_milvus(
                parsed_query,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
        
        return results
    
    def _retrieve_from_neo4j(self, parsed_query: Dict) -> Dict:
        """Retrieve structured data from Neo4j."""
        intent = parsed_query['intent']
        parts_town_numbers = parsed_query['parts_town_numbers']
        manufacturer_numbers = parsed_query['manufacturer_numbers']
        model_names = parsed_query['model_names']
        keywords = parsed_query['keywords']
        
        neo4j_data = {
            'parts': [],
            'models': [],
            'relationships': []
        }
        
        # Query by Parts Town number
        if parts_town_numbers:
            for part_number in parts_town_numbers:
                part_info = self._get_part_by_parts_town_number(part_number)
                if part_info:
                    neo4j_data['parts'].append(part_info)
        
        # Query by manufacturer number
        if manufacturer_numbers:
            for mfr_number in manufacturer_numbers:
                part_info = self._get_part_by_manufacturer_number(mfr_number)
                if part_info:
                    neo4j_data['parts'].append(part_info)
        
        # Query by model name
        if model_names:
            for model_name in model_names:
                model_info = self._get_model_info(model_name)
                if model_info:
                    neo4j_data['models'].append(model_info)
        
        # If no specific entities found, do keyword search
        if not neo4j_data['parts'] and not neo4j_data['models'] and keywords:
            # Search for parts by keywords
            parts_by_keywords = self._search_parts_by_keywords(keywords)
            neo4j_data['parts'].extend(parts_by_keywords)
            
            # Search for models by keywords
            models_by_keywords = self._search_models_by_keywords(keywords)
            neo4j_data['models'].extend(models_by_keywords)
        
        # Get relationships
        neo4j_data['relationships'] = self._get_relationships(neo4j_data)
        
        return neo4j_data
    
    def _get_part_by_parts_town_number(self, parts_town_number: str) -> Optional[Dict]:
        """Get part information by Parts Town #."""
        query = """
        MATCH (p:Part)
        WHERE p.`Parts Town #` = $parts_town_number
           OR p.name = $parts_town_number
        OPTIONAL MATCH (m:Model)-[:HAS_PART]->(p)
        OPTIONAL MATCH (p)-[:HAS_MANUAL]->(pdf:PDF)
        RETURN p, 
               collect(DISTINCT m.name) as models,
               collect(DISTINCT pdf.url) as pdf_urls
        LIMIT 1
        """
        
        result = self.neo4j.execute_query(query, {'parts_town_number': parts_town_number})
        
        if result:
            record = result[0]
            part_node = record['p']
            return {
                'parts_town_number': parts_town_number,
                'properties': dict(part_node),
                'models': [m for m in record['models'] if m],
                'pdf_urls': [url for url in record['pdf_urls'] if url]
            }
        return None
    
    def _get_part_by_manufacturer_number(self, manufacturer_number: str) -> Optional[Dict]:
        """Get part information by Manufacturer #."""
        query = """
        MATCH (p:Part)
        WHERE p.`Manufacture #` = $manufacturer_number
           OR p.`Manufacturer #` = $manufacturer_number
        OPTIONAL MATCH (m:Model)-[:HAS_PART]->(p)
        OPTIONAL MATCH (p)-[:HAS_MANUAL]->(pdf:PDF)
        RETURN p,
               collect(DISTINCT m.name) as models,
               collect(DISTINCT pdf.url) as pdf_urls
        LIMIT 1
        """
        
        result = self.neo4j.execute_query(query, {'manufacturer_number': manufacturer_number})
        
        if result:
            record = result[0]
            part_node = record['p']
            return {
                'manufacturer_number': manufacturer_number,
                'properties': dict(part_node),
                'models': [m for m in record['models'] if m],
                'pdf_urls': [url for url in record['pdf_urls'] if url]
            }
        return None
    
    def _get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get model information."""
        query = """
        MATCH (m:Model {name: $model_name})
        OPTIONAL MATCH (m)-[:HAS_PART]->(p:Part)
        RETURN m,
               collect(DISTINCT p.name) as parts,
               collect(DISTINCT p.`Parts Town #`) as parts_town_numbers
        LIMIT 1
        """
        
        result = self.neo4j.execute_query(query, {'model_name': model_name})
        
        if result:
            record = result[0]
            model_node = record['m']
            return {
                'model_name': model_name,
                'properties': dict(model_node),
                'parts': [p for p in record['parts'] if p],
                'parts_town_numbers': [ptn for ptn in record['parts_town_numbers'] if ptn]
            }
        return None
    
    def _search_parts_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for parts by keywords."""
        # Build search query - look for keywords in part descriptions
        keyword_pattern = '|'.join(keywords)
        
        query = """
        MATCH (p:Part)
        WHERE ANY(keyword IN $keywords WHERE 
            toLower(p.Part) CONTAINS toLower(keyword) OR
            toLower(p.Description) CONTAINS toLower(keyword) OR
            toLower(p.name) CONTAINS toLower(keyword))
        OPTIONAL MATCH (m:Model)-[:HAS_PART]->(p)
        OPTIONAL MATCH (p)-[:HAS_MANUAL]->(pdf:PDF)
        RETURN p,
               collect(DISTINCT m.name) as models,
               collect(DISTINCT pdf.url) as pdf_urls
        LIMIT 10
        """
        
        result = self.neo4j.execute_query(query, {'keywords': keywords})
        
        parts = []
        for record in result:
            part_node = record['p']
            parts.append({
                'properties': dict(part_node),
                'models': [m for m in record['models'] if m],
                'pdf_urls': [url for url in record['pdf_urls'] if url]
            })
        
        return parts
    
    def _search_models_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for models by keywords."""
        query = """
        MATCH (m:Model)
        WHERE ANY(keyword IN $keywords WHERE 
            toLower(m.name) CONTAINS toLower(keyword))
        OPTIONAL MATCH (m)-[:HAS_PART]->(p:Part)
        RETURN m,
               collect(DISTINCT p.name) as parts
        LIMIT 10
        """
        
        result = self.neo4j.execute_query(query, {'keywords': keywords})
        
        models = []
        for record in result:
            model_node = record['m']
            models.append({
                'properties': dict(model_node),
                'parts': [p for p in record['parts'] if p]
            })
        
        return models
    
    def _get_relationships(self, neo4j_data: Dict) -> List[Dict]:
        """Get relationships between retrieved entities."""
        relationships = []
        
        # Get model-part relationships
        for model in neo4j_data['models']:
            model_name = model.get('model_name') or model.get('properties', {}).get('name')
            if model_name:
                query = """
                MATCH (m:Model {name: $model_name})-[:HAS_PART]->(p:Part)
                RETURN p.name as part_name, p.`Parts Town #` as parts_town_number
                LIMIT 20
                """
                result = self.neo4j.execute_query(query, {'model_name': model_name})
                for record in result:
                    relationships.append({
                        'type': 'HAS_PART',
                        'from': model_name,
                        'to': record.get('part_name'),
                        'parts_town_number': record.get('parts_town_number')
                    })
        
        return relationships
    
    def _retrieve_from_milvus(self,
                              parsed_query: Dict,
                              top_k: int = 5,
                              similarity_threshold: float = 0.7) -> List[Dict]:
        """Retrieve relevant PDF chunks from Milvus."""
        if not self.milvus or not self.embedding_generator:
            return []
        
        query_text = parsed_query['query_text']
        parts_town_numbers = parsed_query['parts_town_numbers']
        
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embeddings(query_text)
        
        # Build filter expression if we have specific part numbers
        filter_expr = None
        if parts_town_numbers:
            # Filter by parts_town_number
            part_filters = [f"parts_town_number == '{ptn}'" for ptn in parts_town_numbers]
            filter_expr = " || ".join(part_filters)
        
        # Search in Milvus
        search_results = self.milvus.search(
            query_embedding=query_embedding[0],  # Get first (and only) embedding
            top_k=top_k * 2,  # Get more results to filter by threshold
            filter_expr=filter_expr
        )
        
        # Filter by similarity threshold
        # Note: Milvus uses L2 distance (lower is better)
        # Convert similarity threshold (0.7) to distance threshold
        # For cosine similarity: similarity = 1 - (distance^2 / 2)
        # For L2 distance, we'll use a more lenient threshold
        # Typical L2 distances for similar vectors: 0.0-1.0, so threshold ~0.5 works for similarity 0.7
        distance_threshold = 0.5  # Adjust based on your embedding space
        
        filtered_results = []
        for result in search_results:
            distance = result.get('distance', float('inf'))
            # Convert L2 distance to approximate similarity score
            # Simple conversion: similarity ≈ 1 / (1 + distance)
            similarity_score = 1.0 / (1.0 + distance)
            
            if similarity_score >= similarity_threshold:
                filtered_results.append({
                    'text': result.get('text', ''),
                    'parts_town_number': result.get('parts_town_number', ''),
                    'manufacturer_number': result.get('manufacturer_number', ''),
                    'pdf_url': result.get('pdf_url', ''),
                    'page_number': result.get('page_number', 0),
                    'similarity': similarity_score,
                    'distance': distance
                })
        
        # Return top_k results
        return filtered_results[:top_k]
