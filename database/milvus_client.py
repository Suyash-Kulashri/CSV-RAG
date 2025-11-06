"""
Milvus vector database client for storing and searching PDF embeddings.
"""
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
    MilvusException
)
from typing import List, Dict, Optional
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
import os


# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class MilvusClient:
    """Client for interacting with Milvus vector database."""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 collection_name: str = "partstown_pdfs"):
        """
        Initialize Milvus client.
        
        Args:
            host: Milvus host (defaults to MILVUS_HOST env var or 'localhost')
            port: Milvus port (defaults to MILVUS_PORT env var or 19531)
            collection_name: Name of the collection to use
        """
        self.host = host or os.getenv("MILVUS_HOST", "localhost")
        self.port = port or int(os.getenv("MILVUS_PORT", "19531"))
        self.collection_name = collection_name
        
        # Connect to Milvus
        self._connect()
        
        # Initialize collection
        self._setup_collection()
    
    def _connect(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            print(f"✓ Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            print(f"✗ Failed to connect to Milvus: {e}")
            raise
    
    def _setup_collection(self):
        """
        Set up the collection schema and create if it doesn't exist.
        Schema includes:
        - id: Primary key (auto-generated)
        - embedding: Vector field (1024 dimensions for BGE-M3)
        - text: Chunk text
        - parts_town_number: Parts Town # identifier
        - manufacturer_number: Manufacturer # identifier
        - pdf_url: URL of the PDF
        - page_number: Page number in PDF
        - chunk_index: Index of chunk in page
        """
        # Check if collection exists
        if utility.has_collection(self.collection_name):
            print(f"✓ Collection '{self.collection_name}' already exists")
            self.collection = Collection(self.collection_name)
            return
        
        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),  # BGE-M3 dimension
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="parts_town_number", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="manufacturer_number", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="pdf_url", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="page_number", dtype=DataType.INT64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Partstown PDF chunks with embeddings"
        )
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # Create index on embedding field
        index_params = {
            "metric_type": "L2",  # L2 distance for similarity search
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        print(f"✓ Created collection '{self.collection_name}' with index")
    
    def insert_chunks(self, chunks: List[Dict], embeddings: np.ndarray):
        """
        Insert PDF chunks with embeddings into Milvus.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            embeddings: Numpy array of embeddings (shape: [num_chunks, embedding_dim])
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")
        
        # Prepare data for insertion
        texts = [chunk['text'] for chunk in chunks]
        metadata_list = [chunk['metadata'] for chunk in chunks]
        
        data = [
            embeddings.tolist(),  # Convert numpy array to list
            texts,
            [meta.get('parts_town_number', '') for meta in metadata_list],
            [meta.get('manufacturer_number', '') for meta in metadata_list],
            [meta.get('pdf_url', '') for meta in metadata_list],
            [meta.get('page_number', 0) for meta in metadata_list],
            [meta.get('chunk_index', 0) for meta in metadata_list],
        ]
        
        # Insert data
        self.collection.insert(data)
        self.collection.flush()
        
        print(f"✓ Inserted {len(chunks)} chunks into Milvus")
    
    def search(self, 
               query_embedding: np.ndarray,
               top_k: int = 5,
               filter_expr: str = None) -> List[Dict]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_expr: Optional filter expression (e.g., "parts_town_number == 'TRNBRG00104'")
            
        Returns:
            List of search results with text and metadata
        """
        # Load collection into memory
        self.collection.load()
        
        # Prepare search parameters
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        # Perform search
        try:
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["text", "parts_town_number", "manufacturer_number", "pdf_url", "page_number"]
            )
        except Exception as e:
            print(f"Error during Milvus search: {e}")
            # Try without filter if filter caused the error
            if filter_expr:
                try:
                    results = self.collection.search(
                        data=[query_embedding.tolist()],
                        anns_field="embedding",
                        param=search_params,
                        limit=top_k,
                        output_fields=["text", "parts_town_number", "manufacturer_number", "pdf_url", "page_number"]
                    )
                except Exception as e2:
                    print(f"Error during Milvus search without filter: {e2}")
                    return []
            else:
                return []
        
        # Format results - access entity data correctly for pymilvus 2.6.x
        formatted_results = []
        for hits in results:
            for hit in hits:
                try:
                    # In pymilvus 2.6.x, entity fields are accessed as attributes
                    # Check if entity exists and has the expected structure
                    if hasattr(hit, 'entity') and hit.entity:
                        entity = hit.entity
                        formatted_results.append({
                            'id': hit.id,
                            'distance': float(hit.distance),
                            'text': str(getattr(entity, 'text', '')),
                            'parts_town_number': str(getattr(entity, 'parts_town_number', '')),
                            'manufacturer_number': str(getattr(entity, 'manufacturer_number', '')),
                            'pdf_url': str(getattr(entity, 'pdf_url', '')),
                            'page_number': int(getattr(entity, 'page_number', 0)),
                        })
                    else:
                        # Entity data not available, return minimal result
                        formatted_results.append({
                            'id': hit.id,
                            'distance': float(hit.distance),
                            'text': '',
                            'parts_town_number': '',
                            'manufacturer_number': '',
                            'pdf_url': '',
                            'page_number': 0,
                        })
                except Exception as e:
                    print(f"Warning: Error extracting entity data: {e}")
                    # Return minimal result on error
                    formatted_results.append({
                        'id': hit.id,
                        'distance': float(hit.distance),
                        'text': '',
                        'parts_town_number': '',
                        'manufacturer_number': '',
                        'pdf_url': '',
                        'page_number': 0,
                    })
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        if not utility.has_collection(self.collection_name):
            return {'entity_count': 0}
        
        self.collection.load()
        stats = {
            'entity_count': self.collection.num_entities,
            'collection_name': self.collection_name
        }
        return stats
    
    def query_data(self, 
                   limit: int = 100,
                   offset: int = 0,
                   filter_expr: str = None,
                   output_fields: List[str] = None) -> List[Dict]:
        """
        Query data from the collection.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            filter_expr: Optional filter expression (e.g., "parts_town_number == 'TRNBRG00104'")
            output_fields: List of fields to return (defaults to all except embedding)
            
        Returns:
            List of records with their data
        """
        if not utility.has_collection(self.collection_name):
            return []
        
        self.collection.load()
        
        # Default output fields (exclude embedding to save space, but can include it if needed)
        if output_fields is None:
            output_fields = ["id", "text", "parts_town_number", "manufacturer_number", 
                           "pdf_url", "page_number", "chunk_index"]
        
        # Build query expression
        expr = f"id >= {offset}"
        if filter_expr:
            expr = f"{expr} && {filter_expr}"
        
        # Query data
        try:
            results = self.collection.query(
                expr=expr,
                output_fields=output_fields,
                limit=limit
            )
            return results
        except Exception as e:
            print(f"Error querying data: {e}")
            return []
    
    def get_all_pdf_urls(self) -> List[str]:
        """Get all unique PDF URLs in the collection."""
        if not utility.has_collection(self.collection_name):
            return []
        
        self.collection.load()
        
        # Query to get unique PDF URLs
        results = self.collection.query(
            expr="id >= 0",
            output_fields=["pdf_url"],
            limit=100000  # Large limit to get all
        )
        
        pdf_urls = list(set([r.get('pdf_url', '') for r in results if r.get('pdf_url')]))
        return pdf_urls
    
    def get_pdf_stats(self) -> Dict:
        """Get statistics grouped by PDF URL."""
        if not utility.has_collection(self.collection_name):
            return {}
        
        self.collection.load()
        
        # Query all records
        results = self.collection.query(
            expr="id >= 0",
            output_fields=["pdf_url", "parts_town_number", "page_number"],
            limit=100000
        )
        
        # Group by PDF URL
        pdf_stats = {}
        for r in results:
            pdf_url = r.get('pdf_url', 'Unknown')
            if pdf_url not in pdf_stats:
                pdf_stats[pdf_url] = {
                    'chunk_count': 0,
                    'pages': set(),
                    'parts_town_numbers': set()
                }
            
            pdf_stats[pdf_url]['chunk_count'] += 1
            if r.get('page_number'):
                pdf_stats[pdf_url]['pages'].add(r.get('page_number'))
            if r.get('parts_town_number'):
                pdf_stats[pdf_url]['parts_town_numbers'].add(r.get('parts_town_number'))
        
        # Convert sets to lists for JSON serialization
        for pdf_url in pdf_stats:
            pdf_stats[pdf_url]['pages'] = sorted(list(pdf_stats[pdf_url]['pages']))
            pdf_stats[pdf_url]['parts_town_numbers'] = sorted(list(pdf_stats[pdf_url]['parts_town_numbers']))
        
        return pdf_stats
    
    def clear_collection(self):
        """Clear all data from the collection."""
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            print(f"✓ Dropped collection '{self.collection_name}'")
            # Recreate collection
            self._setup_collection()
        else:
            print(f"Collection '{self.collection_name}' does not exist")
