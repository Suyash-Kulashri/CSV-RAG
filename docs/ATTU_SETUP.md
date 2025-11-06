# Attu Setup Guide - Milvus Web UI

Attu is a web-based GUI for managing and visualizing your Milvus vector database. It allows you to:
- View collections and their schemas
- Browse stored data and embeddings
- Search and query vectors
- Monitor database statistics
- Manage collections

## Quick Start

**Attu is already configured in your `docker-compose.yml`!**

### Access Attu

1. **Open your web browser**
2. **Navigate to:** `http://localhost:3001`
   - Note: Port 3001 is used (as configured in your docker-compose.yml)
3. **You should see the Attu connection screen**

### Connect to Milvus

When you first open Attu:

1. **Connection Settings:**
   - **Address:** `localhost` (or `127.0.0.1`)
   - **Port:** `19531` (your Milvus port from docker-compose.yml)
   - **Username:** Leave empty (default)
   - **Password:** Leave empty (default)

2. **Click "Connect"**

3. **You should now see the Attu dashboard!**

## Step-by-Step Setup (If Not Already Running)

### Option A: Using Docker Compose (Already Configured)

Your `docker-compose.yml` already includes Attu! Just start it:

```bash
docker-compose up -d attu
```

Or restart everything:
```bash
docker-compose restart
```

### Option B: Using Docker Run (Standalone)

If you prefer to run Attu separately:

```bash
docker run -d \
  --name attu \
  -p 3000:3000 \
  -e MILVUS_URL=localhost:19531 \
  zilliz/attu:v2.3.4
```

Then access at: `http://localhost:3000`

## Navigate Attu Interface

### Main Dashboard
- **Overview:** Shows database statistics
- **Collections:** Lists all collections in Milvus
- **Search:** Query vectors and search
- **System View:** Monitor system resources

### Collections View
1. **Click "Collections"** in the left sidebar
2. **You should see:** `partstown_pdfs` collection (after ingesting data)
3. **Click on the collection** to view details:
   - **Schema:** Field definitions (embedding, text, metadata fields)
   - **Data:** Browse stored chunks
   - **Indexes:** View vector indexes
   - **Statistics:** Collection stats (entity count, etc.)

### Viewing Your Data
1. **Go to Collections → partstown_pdfs**
2. **Click "Data" tab**
3. **You'll see:**
   - Text chunks (from PDFs)
   - Parts Town # values
   - Manufacturer # values
   - PDF URLs
   - Page numbers
   - Chunk indices
   - Embedding vectors (1024 dimensions for BGE-M3)

### Searching Vectors
1. **Go to "Search" in the sidebar**
2. **Select collection:** `partstown_pdfs`
3. **Enter a query:**
   - Type your search text (e.g., "bearing installation")
   - Attu will generate embeddings and find similar chunks
   - Set Top-K (number of results, e.g., 5 or 10)
4. **View results** with similarity scores and metadata

## What You Can Do in Attu

### After Ingesting Your CSV:

1. **View Collection:**
   - Go to Collections → `partstown_pdfs`
   - See total number of chunks stored
   - View collection schema

2. **Browse Data:**
   - Click "Data" tab
   - See all PDF chunks with metadata
   - Filter by Parts Town # or PDF URL
   - View raw text content
   - See page numbers and chunk indices

3. **Search:**
   - Use semantic search to find relevant chunks
   - Query by text (e.g., "bearing installation", "valve replacement")
   - See similarity scores
   - Filter results by metadata

4. **Verify Ingestion:**
   - Check that all PDFs were processed
   - Verify chunks have correct metadata
   - Confirm embeddings are stored (1024 dimensions)
   - See total entity count

## Troubleshooting

**Can't connect to Milvus:**
- Verify Milvus is running: `docker ps | grep milvus`
- Check your Milvus port: Your docker-compose uses port `19531`
- Try using `127.0.0.1` instead of `localhost`
- Check Attu logs: `docker logs csvrag-milvus-attu`

**Attu shows "Connection Failed":**
- Make sure Milvus container (`csvrag-milvus-standalone`) is running
- Verify port 19531 is accessible
- Check if Attu container is running: `docker ps | grep attu`

**Collection not showing:**
- Make sure you've ingested data first (run CSV ingestion in Streamlit app)
- Refresh the Attu page (F5)
- Check Milvus directly: `python database/test_milvus_connection.py`

**Wrong port:**
- Your setup uses port 3001 for Attu (not 3000)
- Access at: `http://localhost:3001`
- Milvus is on port 19531 (not 19530)

## Quick Commands

```bash
# Check if Attu is running
docker ps | grep attu

# Start Attu (if using docker-compose)
docker-compose up -d attu

# Stop Attu
docker stop csvrag-milvus-attu

# View Attu logs
docker logs csvrag-milvus-attu

# Restart Attu
docker restart csvrag-milvus-attu

# Restart entire Milvus stack
docker-compose restart
```

## Access URLs

- **Attu Web UI:** http://localhost:3001
- **Milvus API:** localhost:19531
- **MinIO Console:** http://localhost:9011
  - Username: `minioadmin`
  - Password: `minioadmin`

## Tips

- **Refresh data:** Click refresh icon (🔄) to see latest data after ingestion
- **Export data:** You can export collection data from Attu for analysis
- **Monitor performance:** Use System View to check resource usage
- **Multiple collections:** Attu can manage multiple Milvus collections
- **Search tips:** Use specific technical terms for better results (e.g., "bearing", "valve", "sensor")

## Next Steps

Once you can see your data in Attu:
1. ✅ Verify PDF chunks are stored correctly
2. ✅ Check metadata (Parts Town #, PDF URLs, etc.)
3. ✅ Test semantic search functionality
4. ✅ Verify all PDFs from CSV were processed
5. ⏳ Ready for Phase 3: Building the chat interface!

Your Milvus data is now fully visible and manageable through Attu's web interface!

## Example Workflow

1. **Ingest CSV in Streamlit app**
2. **Open Attu:** http://localhost:3001
3. **Connect to Milvus:** localhost:19531
4. **View Collection:** Collections → partstown_pdfs
5. **Browse Data:** See all PDF chunks
6. **Test Search:** Try searching for "bearing" or "valve"
7. **Verify:** Check that metadata matches your CSV data


