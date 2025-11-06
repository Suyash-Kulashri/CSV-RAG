"""
Module for ingesting CSV data into Neo4j graph database.
"""
import pandas as pd
from typing import Dict, List, Set
import sys
import os

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.neo4j_client import Neo4jClient


class CSVToNeo4j:
    """Handle CSV ingestion into Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize CSV to Neo4j converter.
        
        Args:
            neo4j_client: Neo4j client instance
        """
        self.neo4j = neo4j_client
        self.processed_parts: Set[str] = set()
        self.processed_models: Set[str] = set()
        self.processed_pdfs: Set[str] = set()
    
    def read_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Read CSV file into pandas DataFrame.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            DataFrame with CSV data
        """
        try:
            df = pd.read_csv(csv_path)
            print(f"✓ Successfully read CSV: {len(df)} rows, {len(df.columns)} columns")
            print(f"  Columns: {list(df.columns)}")
            return df
        except Exception as e:
            raise Exception(f"Error reading CSV: {e}")
    
    def extract_columns(self, df: pd.DataFrame) -> Dict[str, List]:
        """
        Extract all columns from DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary with column names as keys
        """
        columns = {}
        for col in df.columns:
            columns[col] = df[col].tolist()
        return columns
    
    def clean_value(self, value) -> str:
        """
        Clean a value for use as node property.
        
        Args:
            value: Value to clean
            
        Returns:
            Cleaned string value
        """
        if pd.isna(value) or value == '':
            return None
        return str(value).strip()
    
    def ingest_csv(self, csv_path: str, clear_existing: bool = False):
        """
        Main method to ingest CSV into Neo4j.
        
        Args:
            csv_path: Path to CSV file
            clear_existing: Whether to clear existing database before ingestion
        """
        if clear_existing:
            print("Clearing existing database...")
            self.neo4j.clear_database()
        
        # Read CSV
        df = self.read_csv(csv_path)
        
        # Extract columns
        columns = self.extract_columns(df)
        
        print("\nStarting Neo4j ingestion...")
        
        # Process each row
        total_rows = len(df)
        row_num = 0
        for idx, row in df.iterrows():
            row_num += 1
            if row_num % 100 == 0:
                print(f"  Processed {row_num}/{total_rows} rows...")
            
            # Extract model name
            model_name = self.clean_value(row.get('Model'))
            if not model_name:
                continue
            
            # Extract Partstown # as unique identifier (not Part description)
            parts_town_number = self.clean_value(row.get('Parts Town #'))
            if not parts_town_number:
                # Fallback to Part description if Parts Town # is missing
                parts_town_number = self.clean_value(row.get('Part'))
                if not parts_town_number:
                    continue
            
            # Extract PDF URLs (handle multiple PDF link columns)
            pdf_urls = []
            for col in df.columns:
                if col.startswith('PDF Link') or 'PDF' in col:
                    pdf_url = self.clean_value(row.get(col))
                    if pdf_url and pdf_url.strip():
                        pdf_urls.append(pdf_url)
            
            # Create model node (only once per unique model)
            if model_name not in self.processed_models:
                self.neo4j.create_model_node(model_name)
                self.processed_models.add(model_name)
            
            # Create part node (only once per unique Parts Town #)
            if parts_town_number not in self.processed_parts:
                # Extract all part properties including Part description
                part_properties = {}
                for col in df.columns:
                    # Skip Model (separate node), Parts Town # (node identifier), and PDF columns (handled separately)
                    if col in ['Model', 'Parts Town #'] or col.startswith('PDF Link') or 'PDF' in col:
                        continue
                    
                    value = self.clean_value(row.get(col))
                    if value is not None:
                        # Convert column name to property name (remove spaces, handle special chars)
                        prop_name = col.replace(' ', '_').replace('#', 'number').replace('/', '_').replace('&amp;', 'and')
                        part_properties[prop_name] = value
                
                # Use Parts Town # as the unique identifier
                self.neo4j.create_part_node(parts_town_number, part_properties)
                self.processed_parts.add(parts_town_number)
            
            # Create relationship between model and part (using Parts Town #)
            self.neo4j.create_model_part_relationship(model_name, parts_town_number)
            
            # Handle PDFs if they exist
            for pdf_url in pdf_urls:
                if pdf_url and pdf_url.strip():
                    # Create PDF node (only once per unique URL)
                    if pdf_url not in self.processed_pdfs:
                        self.neo4j.create_pdf_node(pdf_url)
                        self.processed_pdfs.add(pdf_url)
                    
                    # Create relationship between part and PDF (using Parts Town #)
                    self.neo4j.create_part_pdf_relationship(parts_town_number, pdf_url)
        
        print(f"\n✓ Ingestion complete!")
        print(f"  - Models processed: {len(self.processed_models)}")
        print(f"  - Parts processed: {len(self.processed_parts)}")
        print(f"  - PDFs processed: {len(self.processed_pdfs)}")
        print(f"  - Total rows processed: {row_num}")
        
        # Verify data was written to Neo4j
        try:
            stats = self.neo4j.get_database_stats()
            print(f"\n📊 Database Verification:")
            print(f"  - Total nodes in database: {stats['total_nodes']}")
            print(f"  - Total relationships in database: {stats['total_relationships']}")
            if stats['by_label']:
                print(f"  - Nodes by label:")
                for label, count in stats['by_label'].items():
                    print(f"    - {label}: {count}")
        except Exception as e:
            print(f"  ⚠️  Could not verify database stats: {e}")


if __name__ == "__main__":
    # Example usage - will use environment variables from .env file
    # Make sure you have created .env file with NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    neo4j_client = Neo4jClient()  # Uses environment variables from .env
    
    converter = CSVToNeo4j(neo4j_client)
    
    # Replace with your CSV path
    csv_path = "test_model.csv"
    converter.ingest_csv(csv_path, clear_existing=True)
    
    neo4j_client.close()

