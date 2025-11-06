"""
Quick test script to verify Neo4j connection.
Run this after setting up your Neo4j instance.
"""
import sys
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Find .env file in project root (parent of database folder)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from database.neo4j_client import Neo4jClient


def test_neo4j_connection(uri: str, user: str, password: str):
    """Test Neo4j connection."""
    print(f"\n🔍 Testing Neo4j connection...")
    print(f"   URI: {uri}")
    print(f"   User: {user}")
    print()
    
    try:
        client = Neo4jClient(uri=uri, user=user, password=password)
        
        # Test query
        result = client.execute_query("RETURN 'Connection successful!' as message")
        print(f"✓ {result[0]['message']}")
        
        # Check database info
        try:
            db_info = client.execute_query("SHOW DATABASES")
            if db_info:
                print(f"✓ Available databases: {len(db_info)} found")
        except:
            try:
                db_info = client.execute_query("CALL db.info()")
                if db_info:
                    print(f"✓ Database info retrieved")
            except:
                print(f"✓ Connection verified (database info query not available)")
        
        client.close()
        print("\n✅ Neo4j is ready to use!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPlease check:")
        print("  1. Neo4j instance is running")
        print("  2. URI is correct (bolt://localhost:7687 or neo4j://127.0.0.1:7687)")
        print("  3. Password is correct")
        print("  4. Database has been created\n")
        return False


if __name__ == "__main__":
    import sys
    
    # Get connection settings from environment variables or command line
    # Priority: command line args > environment variables > defaults
    
    # Get URI from env or use default
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    
    # Get user from env or use default
    USER = os.getenv("NEO4J_USER", "neo4j")
    
    # Get password: command line arg > env var > default
    if len(sys.argv) > 1:
        PASSWORD = sys.argv[1]
        print(f"\n📝 Using password from command line argument")
    else:
        PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
        if PASSWORD == "password":
            print("\n⚠️  Using default password 'password'.")
            print("   Set NEO4J_PASSWORD in .env file or run:")
            print("   python database/test_neo4j_connection.py YOUR_PASSWORD\n")
        else:
            print(f"\n📝 Using password from .env file")
    
    print("=" * 50)
    print("Neo4j Connection Test")
    print("=" * 50)
    print(f"   Loading from: {'command line' if len(sys.argv) > 1 else '.env file'}")
    
    test_neo4j_connection(URI, USER, PASSWORD)

