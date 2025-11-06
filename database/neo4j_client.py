"""
Neo4j database client for managing connections and operations.
"""
from neo4j import GraphDatabase
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Find .env file in project root (parent of this file's directory)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Neo4jClient:
    """Client for interacting with Neo4j database."""
    
    def __init__(self, uri: str = None, 
                 user: str = None, 
                 password: str = None):
        """
        Initialize Neo4j client.
        
        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        # Use provided values or fall back to environment variables
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.verify_connectivity()
    
    def verify_connectivity(self):
        """Verify connection to Neo4j."""
        try:
            self.driver.verify_connectivity()
            print("✓ Successfully connected to Neo4j")
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j driver connection."""
        self.driver.close()
    
    def execute_query(self, query: str, parameters: dict = None, database: str = None):
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            database: Database name (optional, uses default if not specified)
            
        Returns:
            Query result
        """
        with self.driver.session(database=database) as session:
            try:
                result = session.run(query, parameters or {})
                # Consume the result to ensure transaction commits
                records = [record for record in result]
                return records
            except Exception as e:
                print(f"Error executing query: {e}")
                print(f"Query: {query[:100]}...")
                raise
    
    def clear_database(self):
        """Clear all nodes and relationships from the database."""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        print("✓ Database cleared")
    
    def create_model_node(self, model_name: str, properties: dict = None):
        """
        Create or update a Model node.
        
        Args:
            model_name: Name/ID of the model
            properties: Additional properties for the model
        """
        properties = properties or {}
        properties['name'] = model_name
        
        query = """
        MERGE (m:Model {name: $name})
        SET m += $properties
        RETURN m
        """
        self.execute_query(query, {'name': model_name, 'properties': properties})
    
    def create_part_node(self, part_name: str, properties: dict):
        """
        Create or update a Part node.
        
        Args:
            part_name: Name/description of the part
            properties: Properties of the part
        """
        properties['name'] = part_name
        
        query = """
        MERGE (p:Part {name: $name})
        SET p += $properties
        RETURN p
        """
        self.execute_query(query, {'name': part_name, 'properties': properties})
    
    def create_pdf_node(self, pdf_url: str):
        """
        Create or update a PDF node.
        
        Args:
            pdf_url: URL of the PDF manual
        """
        query = """
        MERGE (pdf:PDF {url: $url})
        SET pdf.url = $url
        RETURN pdf
        """
        self.execute_query(query, {'url': pdf_url})
    
    def create_model_part_relationship(self, model_name: str, part_name: str, properties: dict = None):
        """
        Create relationship between Model and Part.
        
        Args:
            model_name: Name/ID of the model
            part_name: Name/description of the part
            properties: Additional properties for the relationship
        """
        properties = properties or {}
        
        query = """
        MATCH (m:Model {name: $model_name})
        MATCH (p:Part {name: $part_name})
        MERGE (m)-[r:HAS_PART]->(p)
        SET r += $properties
        RETURN r
        """
        self.execute_query(query, {
            'model_name': model_name,
            'part_name': part_name,
            'properties': properties
        })
    
    def create_part_pdf_relationship(self, part_name: str, pdf_url: str):
        """
        Create relationship between Part and PDF.
        
        Args:
            part_name: Name/description of the part
            pdf_url: URL of the PDF manual
        """
        query = """
        MATCH (p:Part {name: $part_name})
        MATCH (pdf:PDF {url: $url})
        MERGE (p)-[r:HAS_MANUAL]->(pdf)
        RETURN r
        """
        self.execute_query(query, {
            'part_name': part_name,
            'url': pdf_url
        })
    
    def get_model_info(self, model_name: str):
        """Get information about a model including its parts."""
        query = """
        MATCH (m:Model {name: $model_name})
        OPTIONAL MATCH (m)-[:HAS_PART]->(p:Part)
        RETURN m, collect(p) as parts
        """
        result = self.execute_query(query, {'model_name': model_name})
        return result[0] if result else None
    
    def get_part_info(self, part_name: str):
        """Get information about a part including its models and PDFs."""
        query = """
        MATCH (p:Part {name: $part_name})
        OPTIONAL MATCH (m:Model)-[:HAS_PART]->(p)
        OPTIONAL MATCH (p)-[:HAS_MANUAL]->(pdf:PDF)
        RETURN p, collect(DISTINCT m) as models, collect(DISTINCT pdf) as pdfs
        """
        result = self.execute_query(query, {'part_name': part_name})
        return result[0] if result else None
    
    def get_database_stats(self):
        """Get statistics about the database."""
        stats = {}
        
        # Count nodes
        query = "MATCH (n) RETURN count(n) as count"
        result = self.execute_query(query)
        stats['total_nodes'] = result[0]['count'] if result else 0
        
        # Count relationships
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        result = self.execute_query(query)
        stats['total_relationships'] = result[0]['count'] if result else 0
        
        # Count by label
        query = "MATCH (n) RETURN labels(n)[0] as label, count(n) as count"
        result = self.execute_query(query)
        stats['by_label'] = {record['label']: record['count'] for record in result}
        
        return stats

