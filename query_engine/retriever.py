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
            'milvus_results': [],
            'query_intent': parsed_query.get('intent', 'general')  # Pass intent to response builder
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
        """Get model information with limited part details."""
        # First, get model and total part count
        count_query = """
        MATCH (m:Model {name: $model_name})
        OPTIONAL MATCH (m)-[:HAS_PART]->(p:Part)
        WITH m, count(p) as total_parts
        RETURN m, total_parts
        LIMIT 1
        """
        
        count_result = self.neo4j.execute_query(count_query, {'model_name': model_name})
        
        if not count_result:
            return None
        
        model_node = count_result[0]['m']
        total_parts = count_result[0]['total_parts']
        
        # Determine how many parts to show
        # If <= 7 parts: show all
        # If > 7 parts: show first 5 Parts Town #, then "and X more"
        limit = total_parts if total_parts <= 7 else 5
        
        # Get Parts Town # for the parts we'll show
        parts_query = """
        MATCH (m:Model {name: $model_name})-[:HAS_PART]->(p:Part)
        RETURN p.`Parts Town #` as parts_town_number
        LIMIT $limit
        """
        
        parts_result = self.neo4j.execute_query(parts_query, {'model_name': model_name, 'limit': limit})
        
        # Get Parts Town numbers
        parts_town_numbers = [record.get('parts_town_number') for record in parts_result if record.get('parts_town_number')]
        
        # Calculate remaining parts
        remaining_parts = max(0, total_parts - len(parts_town_numbers))
        
        return {
            'model_name': model_name,
            'properties': dict(model_node),
            'total_parts': total_parts,
            'parts_town_numbers': parts_town_numbers,  # Parts Town # to show
            'remaining_parts': remaining_parts,  # Remaining parts not shown
            'show_all': total_parts <= 7  # Flag to indicate if all parts are shown
        }
    
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
            print("⚠️  Milvus or embedding generator not available")
            return []
        
        query_text = parsed_query['query_text']
        parts_town_numbers = parsed_query['parts_town_numbers']
        
        print(f"\n🔍 Milvus Retrieval:")
        print(f"  Query: {query_text}")
        print(f"  Parts queried: {parts_town_numbers}")
        
        # Check if any of the queried parts actually have PDFs
        parts_with_pdfs = self._get_parts_with_pdfs(parts_town_numbers)
        
        print(f"  Parts with PDFs in Neo4j: {parts_with_pdfs}")
        
        # If no parts have PDFs, skip Milvus
        if parts_town_numbers and not parts_with_pdfs:
            print("  ⚠️  No parts have PDFs - skipping Milvus search")
            return []
        
        # Generate query embedding
        print(f"  Generating embeddings...")
        query_embedding = self.embedding_generator.generate_embeddings(query_text)
        
        # Build filter expression
        # CRITICAL: ALWAYS filter by part when a part is in context
        # This ensures excerpts are ONLY relevant to the specific part
        filter_expr = None
        
        if parts_with_pdfs:
            # Part-specific query - STRICTLY filter to show only relevant excerpts
            part_filters = [f"parts_town_number == '{ptn}'" for ptn in parts_with_pdfs]
            filter_expr = " || ".join(part_filters)
            print(f"  ✅ Filtering by part for relevance: {filter_expr}")
        else:
            # No parts specified - search all PDFs
            print(f"  No part context - searching all PDFs")
        
        # Search in Milvus
        print(f"  Searching Milvus for top {top_k * 2} results...")
        search_results = self.milvus.search(
            query_embedding=query_embedding[0],  # Get first (and only) embedding
            top_k=top_k * 2,  # Get more results to filter by threshold
            filter_expr=filter_expr
        )
        
        print(f"  Raw search results: {len(search_results)} chunks returned")
        
        # Filter by similarity threshold
        # Note: Milvus uses L2 distance (lower is better)
        # For L2 distance: smaller values = more similar
        # Typical L2 distances: 0.0 (identical) to 2.0+ (very different)
        # Using a more lenient distance threshold to get more results
        max_distance = 1.5  # Adjust based on testing (lower = stricter, higher = more lenient)
        
        filtered_results = []
        for result in search_results:
            distance = result.get('distance', float('inf'))
            
            # Convert L2 distance to similarity score for readability
            # similarity_score = 1.0 / (1.0 + distance)
            # However, we'll filter by raw distance for L2
            
            # More lenient filtering - accept results with reasonable distance
            if distance <= max_distance:
                similarity_score = 1.0 / (1.0 + distance)
                filtered_results.append({
                    'text': result.get('text', ''),
                    'parts_town_number': result.get('parts_town_number', ''),
                    'manufacturer_number': result.get('manufacturer_number', ''),
                    'pdf_url': result.get('pdf_url', ''),
                    'page_number': result.get('page_number', 0),
                    'similarity': similarity_score,
                    'distance': distance
                })
        
        # Sort by distance (lower is better) and return top_k results
        filtered_results.sort(key=lambda x: x['distance'])
        
        print(f"  ✓ Found {len(filtered_results)} relevant chunks (max distance: {max_distance})")
        if filtered_results:
            print(f"    Best match distance: {filtered_results[0]['distance']:.4f}")
            print(f"    Worst match distance: {filtered_results[-1]['distance']:.4f}")
            for i, res in enumerate(filtered_results[:3], 1):
                print(f"    [{i}] Part: {res['parts_town_number']}, Page: {res['page_number']}, Distance: {res['distance']:.4f}")
        
        # If no results with filter, try searching without filter
        if not filtered_results and filter_expr:
            print(f"  ⚠️  No results with filter - trying broader search...")
            search_results = self.milvus.search(
                query_embedding=query_embedding[0],
                top_k=top_k * 2,
                filter_expr=None  # No filter
            )
            print(f"  Broader search returned: {len(search_results)} chunks")
            
            for result in search_results:
                distance = result.get('distance', float('inf'))
                if distance <= max_distance:
                    similarity_score = 1.0 / (1.0 + distance)
                    filtered_results.append({
                        'text': result.get('text', ''),
                        'parts_town_number': result.get('parts_town_number', ''),
                        'manufacturer_number': result.get('manufacturer_number', ''),
                        'pdf_url': result.get('pdf_url', ''),
                        'page_number': result.get('page_number', 0),
                        'similarity': similarity_score,
                        'distance': distance
                    })
            
            filtered_results.sort(key=lambda x: x['distance'])
            print(f"  ✓ Broader search found {len(filtered_results)} relevant chunks")
        
        return filtered_results[:top_k]
    
    def _get_parts_with_pdfs(self, parts_town_numbers: List[str]) -> List[str]:
        """
        Check which parts have PDF manuals available.
        
        Args:
            parts_town_numbers: List of Parts Town # to check
            
        Returns:
            List of Parts Town # that have PDFs
        """
        if not parts_town_numbers:
            return []
        
        parts_with_pdfs = []
        for ptn in parts_town_numbers:
            query = """
            MATCH (p:Part)
            WHERE p.`Parts Town #` = $parts_town_number OR p.name = $parts_town_number
            OPTIONAL MATCH (p)-[:HAS_MANUAL]->(pdf:PDF)
            RETURN p.name as part_name, collect(pdf.url) as pdf_urls
            LIMIT 1
            """
            result = self.neo4j.execute_query(query, {'parts_town_number': ptn})
            if result and result[0].get('pdf_urls'):
                # Part has PDFs
                pdf_urls = [url for url in result[0]['pdf_urls'] if url]
                if pdf_urls:
                    parts_with_pdfs.append(ptn)
        
        return parts_with_pdfs
