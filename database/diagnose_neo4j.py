"""
Diagnostic script to check Neo4j database contents.
Run this to verify if data exists in your Neo4j database.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

sys.path.append(str(Path(__file__).parent.parent))
from database.neo4j_client import Neo4jClient


def main():
    print("=" * 60)
    print("Neo4j Database Diagnostic")
    print("=" * 60)
    
    try:
        client = Neo4jClient()
        
        # Get database stats
        print("\n📊 Database Statistics:")
        stats = client.get_database_stats()
        print(f"  Total nodes: {stats['total_nodes']}")
        print(f"  Total relationships: {stats['total_relationships']}")
        
        if stats['by_label']:
            print("\n  Nodes by label:")
            for label, count in stats['by_label'].items():
                print(f"    - {label}: {count}")
        
        # Sample some nodes
        print("\n🔍 Sample Data:")
        
        # Get sample models
        query = "MATCH (m:Model) RETURN m LIMIT 5"
        result = client.execute_query(query)
        print(f"\n  Sample Models ({len(result)} found):")
        for record in result[:3]:
            node = record['m']
            print(f"    - {dict(node)}")
        
        # Get sample parts
        query = "MATCH (p:Part) RETURN p LIMIT 5"
        result = client.execute_query(query)
        print(f"\n  Sample Parts ({len(result)} found):")
        for record in result[:3]:
            node = record['p']
            props = dict(node)
            name = props.get('name', 'N/A')
            print(f"    - {name[:50]}...")
        
        # Check relationships
        query = "MATCH (m:Model)-[r:HAS_PART]->(p:Part) RETURN count(*) as count"
        result = client.execute_query(query)
        print(f"\n  Model-Part relationships: {result[0]['count'] if result else 0}")
        
        query = "MATCH (p:Part)-[r:HAS_MANUAL]->(pdf:PDF) RETURN count(*) as count"
        result = client.execute_query(query)
        print(f"  Part-PDF relationships: {result[0]['count'] if result else 0}")
        
        client.close()
        print("\n✅ Diagnostic complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

