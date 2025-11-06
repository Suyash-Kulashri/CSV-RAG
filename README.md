# CSV RAG Chat App

A Streamlit application for querying Partstown Trane parts data using Neo4j graph database and Milvus vector database.

## Project Structure

```
project/
│
├── app.py                 # Main Streamlit app
├── data_ingestion/
│   ├── csv_to_neo4j.py   # Load CSV into Neo4j
│   ├── pdf_to_milvus.py  # Process PDFs into Milvus
│   ├── pdf_downloader.py # Download unique PDFs
│   └── verify_parts.py    # Verify parts ingestion
│
├── database/
│   ├── neo4j_client.py   # Neo4j connection & queries
│   ├── milvus_client.py  # Milvus connection & search
│   ├── test_neo4j_connection.py  # Test Neo4j connection
│   └── diagnose_neo4j.py  # Diagnose Neo4j database
│
├── query_engine/
│   ├── query_parser.py   # Parse user questions
│   ├── retriever.py      # Retrieve from both DBs
│   └── response_builder.py # Combine and format results
│
└── utils/
    ├── embeddings.py     # Generate embeddings
    └── pdf_processor.py  # Extract text from PDFs
```

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` file and update with your Neo4j connection details:
     ```
     NEO4J_URI=bolt://localhost:7687
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=your_password_here
     ```

3. **Set up Neo4j:**
   - Install Neo4j Desktop or Neo4j Community Edition
   - Create a new database instance
   - Create a database (e.g., `partstown`)
   - Update the `.env` file with your connection details
   - Test connection: `python database/test_neo4j_connection.py`

4. **Run the application:**
```bash
streamlit run app.py
```
   
   The app will automatically load connection settings from `.env` file, but you can override them in the UI if needed.

## Usage

1. Open the app in your browser (connection settings are loaded from `.env`)
2. Upload a CSV file with parts data in the sidebar
3. Click "Ingest CSV into Neo4j" to load the data
4. Query the data using the chat interface (coming soon)

**Utility Scripts:**
- Test Neo4j connection: `python database/test_neo4j_connection.py`
- Diagnose database: `python database/diagnose_neo4j.py`
- Verify parts ingestion: `python data_ingestion/verify_parts.py`

## CSV Format

Expected CSV columns:
- `Model`: Model name/ID
- `Part`: Part name/description
- `List Price`: Price of the part
- `Quantity Available`: Available quantity
- `Manufacturer`: Manufacturer name
- `Manufacturer #`: Manufacturer part number
- `Parts Town #`: Parts Town part number
- `Units`: Unit of measurement
- `PDF Link 1`: URL to PDF manual (optional)

## Development Status

- ✅ CSV to Neo4j ingestion
- ⏳ PDF to Milvus ingestion
- ⏳ Chat interface
- ⏳ Query engine

