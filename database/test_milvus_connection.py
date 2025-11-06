"""
Quick test script to verify Milvus connection.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

sys.path.append(str(Path(__file__).parent.parent))
from database.milvus_client import MilvusClient


def test_milvus_connection():
    """Test Milvus connection."""
    print("=" * 60)
    print("Milvus Connection Test")
    print("=" * 60)
    
    try:
        client = MilvusClient()
        stats = client.get_collection_stats()
        
        print("\n✅ Milvus connection successful!")
        print(f"   Collection: {stats.get('collection_name', 'N/A')}")
        print(f"   Entities: {stats.get('entity_count', 0)}")
        print("\n✓ Milvus is ready to use!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPlease check:")
        print("  1. Milvus container is running (docker ps)")
        print("  2. Port 19531 is accessible")
        print("  3. MILVUS_HOST and MILVUS_PORT in .env are correct")
        print("\nTo start Milvus:")
        print("  docker-compose up -d")
        print("  OR")
        print("  docker run -d --name csvrag-milvus-standalone -p 19531:19530 milvusdb/milvus:v2.3.4 milvus run standalone\n")
        return False


if __name__ == "__main__":
    test_milvus_connection()

