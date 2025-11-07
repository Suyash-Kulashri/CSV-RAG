# Milvus Setup Guide

## Step-by-Step Setup Instructions

### 1. Install Dependencies

First, make sure you have the Python dependencies installed:

```bash
pip install -r requirements.txt
```

If you encounter any issues, you may need to install Milvus client specifically:
```bash
pip install pymilvus
```

### 2. Set Up Milvus Using Docker

Since you have Docker Desktop open, we'll use Docker to run Milvus. This is the easiest method.

#### Option A: Using Docker Compose (Recommended)

1. **Create a `docker-compose.yml` file** in your project root:
   ```yaml
   version: '3.5'
   
   services:
     etcd:
       container_name: milvus-etcd
       image: quay.io/coreos/etcd:v3.5.5
       environment:
         - ETCD_AUTO_COMPACTION_MODE=revision
         - ETCD_AUTO_COMPACTION_RETENTION=1000
         - ETCD_QUOTA_BACKEND_BYTES=4294967296
         - ETCD_SNAPSHOT_COUNT=50000
       volumes:
         - etcd_data:/etcd
       command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
       healthcheck:
         test: ["CMD", "etcdctl", "endpoint", "health"]
         interval: 30s
         timeout: 20s
         retries: 3
   
     minio:
       container_name: milvus-minio
       image: minio/minio:RELEASE.2023-03-20T20-16-18Z
       environment:
         MINIO_ACCESS_KEY: minioadmin
         MINIO_SECRET_KEY: minioadmin
       ports:
         - "9001:9001"
         - "9000:9000"
       volumes:
         - minio_data:/minio_data
       command: minio server /minio_data --console-address ":9001"
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
         interval: 30s
         timeout: 20s
         retries: 3
   
     standalone:
       container_name: milvus-standalone
       image: milvusdb/milvus:v2.3.4
       command: ["milvus", "run", "standalone"]
       environment:
         ETCD_ENDPOINTS: etcd:2379
         MINIO_ADDRESS: minio:9000
       volumes:
         - milvus_data:/var/lib/milvus
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
         interval: 30s
         start_period: 90s
         timeout: 20s
         retries: 3
       ports:
         - "19530:19530"
         - "9091:9091"
       depends_on:
         - "etcd"
         - "minio"
   
   volumes:
     etcd_data:
     minio_data:
     milvus_data:
   ```

2. **Start Milvus:**
   ```bash
   docker-compose up -d
   ```

3. **Verify Milvus is running:**
   ```bash
   docker ps
   ```
   You should see three containers running:
   - `milvus-standalone`
   - `milvus-etcd`
   - `milvus-minio`

#### Option B: Using Docker Run (Simpler, but less persistent)

1. **Run Milvus Standalone:**
   ```bash
   docker run -d --name milvus-standalone \
     -p 19530:19530 \
     -p 9091:9091 \
     -v $(pwd)/milvus_data:/var/lib/milvus \
     milvusdb/milvus:v2.3.4 \
     milvus run standalone
   ```

2. **Verify it's running:**
   ```bash
   docker ps | grep milvus
   ```

### 3. Configure Environment Variables

Update your `.env` file with Milvus connection details:

```bash
# Add these lines to your .env file
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

The default values are already set in the code, but it's good to have them in `.env` for clarity.

### 4. Test Milvus Connection

Create a test script to verify Milvus is working:

```bash
python -c "
from database.milvus_client import MilvusClient
try:
    client = MilvusClient()
    stats = client.get_collection_stats()
    print('✅ Milvus connection successful!')
    print(f'Collection: {stats.get(\"collection_name\", \"N/A\")}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

### 5. Verify in Docker Desktop

1. **Open Docker Desktop** (you already have it open)
2. **Go to "Containers"** in the left sidebar
3. **Look for Milvus containers:**
   - `milvus-standalone` (main Milvus server)
   - `milvus-etcd` (if using docker-compose)
   - `milvus-minio` (if using docker-compose)
4. **Check status:** All should show "Running" (green)

### 6. Quick Start Commands

```bash
# Start Milvus (if using docker-compose)
docker-compose up -d

# Check Milvus logs
docker logs milvus-standalone

# Stop Milvus
docker-compose down

# Or if using docker run:
docker stop milvus-standalone
docker rm milvus-standalone
```

### 7. Common Issues

**Connection refused:**
- Make sure Milvus container is running: `docker ps`
- Check if port 19530 is available: `lsof -i :19530`
- Verify `.env` has correct `MILVUS_HOST` and `MILVUS_PORT`

**Container won't start:**
- Check logs: `docker logs milvus-standalone`
- Make sure Docker has enough resources allocated
- Try removing and recreating: `docker rm milvus-standalone` then run again

**Port already in use:**
- Another service might be using port 19530
- Change port in docker command: `-p 19531:19530` and update `.env` accordingly

### 8. Using Milvus Lite (Alternative - No Docker)

If you prefer not to use Docker, you can use Milvus Lite (embedded):

```bash
pip install milvus
```

Then update `milvus_client.py` to use Milvus Lite mode. However, Docker is recommended for production use.

## Next Steps

Once Milvus is running:
1. ✅ Test connection using the test script above
2. ✅ Run your Streamlit app: `streamlit run app.py`
3. ✅ Upload CSV - PDFs will be automatically processed and stored in Milvus
4. ✅ Check Milvus stats in the app after ingestion

## Verification

After setting up, you can verify everything works:

```bash
# Test Neo4j
python database/test_neo4j_connection.py

# Test Milvus (create a simple test)
python -c "from database.milvus_client import MilvusClient; c = MilvusClient(); print('✅ Milvus OK')"
```

Your system is now ready to process PDFs and store them in Milvus!

