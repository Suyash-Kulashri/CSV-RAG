# Neo4j Setup Guide

## Step-by-Step Setup Instructions

### 1. Install Dependencies

First, make sure you have Python dependencies installed:

```bash
pip install -r requirements.txt
```

If you encounter any issues, you may need to install Neo4j driver specifically:
```bash
pip install neo4j
```

### 2. Create Neo4j Instance in Neo4j Desktop

1. **Open Neo4j Desktop** (you should see it open)

2. **Click "Create instance"** button (top right, blue button)

3. **Fill in the details:**
   - **Name**: `csv-rag-project` (or any name you prefer)
   - **Password**: Choose a secure password (remember this!)
   - **Version**: Choose Neo4j 5.x (recommended)
   - Click **"Create"**

4. **Start the instance:**
   - Click the **Play button** (▶️) on your new instance
   - Wait until status shows **"RUNNING"** (green)

5. **Create a database:**
   - Expand the **"Databases"** section on your instance card
   - Click **"Create database"**
   - Name it: `partstown` (or `csvrag`)
   - Click **"Create"**

### 3. Configure Environment Variables

After creating your instance, configure the `.env` file:

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your Neo4j connection details:
   - **NEO4J_URI**: Usually `bolt://localhost:7687` or `neo4j://127.0.0.1:7687`
     - Check your instance card - it shows the URI
   - **NEO4J_USER**: `neo4j` (default)
   - **NEO4J_PASSWORD**: The password you set when creating the instance

   Example `.env` content:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here
   ```

### 4. Test Connection

Run the test script to verify everything works:

```bash
python database/test_neo4j_connection.py
```

The script will automatically load settings from your `.env` file. You can also override the password via command line:
```bash
python database/test_neo4j_connection.py your_password
```

### 5. Run the App

The Streamlit app will automatically load connection settings from `.env`:

```bash
streamlit run app.py
```

You can override settings in the UI if needed, but they're pre-filled from `.env` for convenience.

### 6. Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (copy example and edit)
cp .env.example .env
# Edit .env with your Neo4j details

# Test Neo4j connection (uses .env)
python database/test_neo4j_connection.py

# Diagnose Neo4j database
python database/diagnose_neo4j.py

# Verify parts ingestion
python data_ingestion/verify_parts.py

# Run Streamlit app (uses .env)
streamlit run app.py
```

### 7. Common Issues

**Connection refused:**
- Make sure Neo4j instance is running (green status)
- Check URI matches your instance (bolt:// vs neo4j://)
- Verify `.env` file has correct NEO4J_URI

**Authentication failed:**
- Verify password is correct in `.env` file
- Default username is `neo4j`
- Check NEO4J_PASSWORD in `.env` matches your Neo4j instance password

**Port already in use:**
- If you have multiple instances, they use different ports
- Check the URI shown on your instance card

## Next Steps

Once Neo4j is set up:
1. ✅ Upload CSV file in Streamlit app
2. ✅ Click "Ingest CSV into Neo4j"
3. ✅ Verify data is loaded (check statistics)
4. ⏳ Set up Milvus for PDF processing (next step)
5. ⏳ Build chat interface (next step)

