"""
Verification script to ensure all unique parts from CSV are in Neo4j.
"""
import pandas as pd
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

sys.path.append(str(Path(__file__).parent.parent))
from database.neo4j_client import Neo4jClient


def verify_parts():
    """Verify all unique parts from CSV are in Neo4j."""
    print("=" * 60)
    print("Parts Verification")
    print("=" * 60)
    
    # Read CSV
    csv_path = Path(__file__).parent.parent / "Scrapped_data.csv"
    df = pd.read_csv(csv_path)
    
    # Get unique Parts Town # values from CSV
    csv_unique_parts = set(df['Parts Town #'].dropna().unique())
    print(f"\n📋 CSV Analysis:")
    print(f"  Total rows: {len(df)}")
    print(f"  Unique Parts Town # values: {len(csv_unique_parts)}")
    print(f"  Sample: {list(csv_unique_parts)[:5]}")
    
    # Connect to Neo4j
    try:
        client = Neo4jClient()
        
        # Get all parts from Neo4j
        query = "MATCH (p:Part) RETURN p.name as parts_town_number"
        result = client.execute_query(query)
        neo4j_parts = {record['parts_town_number'] for record in result}
        
        print(f"\n🗄️  Neo4j Analysis:")
        print(f"  Total Part nodes: {len(neo4j_parts)}")
        print(f"  Sample: {list(neo4j_parts)[:5]}")
        
        # Compare
        print(f"\n✅ Verification Results:")
        missing_parts = csv_unique_parts - neo4j_parts
        extra_parts = neo4j_parts - csv_unique_parts
        
        if not missing_parts and not extra_parts:
            print(f"  ✓ All {len(csv_unique_parts)} unique parts from CSV are in Neo4j!")
        else:
            if missing_parts:
                print(f"  ❌ Missing {len(missing_parts)} parts from CSV:")
                for part in sorted(missing_parts):
                    print(f"    - {part}")
            
            if extra_parts:
                print(f"  ⚠️  Extra {len(extra_parts)} parts in Neo4j (not in CSV):")
                for part in sorted(list(extra_parts)[:10]):
                    print(f"    - {part}")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verify_parts()

