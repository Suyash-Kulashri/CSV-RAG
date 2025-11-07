# CSV RAG Chat App

A Streamlit application for querying Partstown Trane parts data using Neo4j graph database and Milvus vector database.

## Project Structure

```
CSV RAG/
│
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Milvus services configuration
├── README.md                   # This file
│
├── data/                       # Data files
│   └── Scrapped_data.csv       # Sample parts data
│
├── data_ingestion/             # Data ingestion modules
│   ├── csv_to_neo4j.py         # CSV → Neo4j ingestion
│   ├── pdf_to_milvus.py        # PDF → Milvus processing
│   ├── pdf_downloader.py       # PDF download utility
│   └── verify_parts.py         # Ingestion verification
│
├── database/                   # Database clients
│   ├── neo4j_client.py         # Neo4j connection & queries
│   ├── milvus_client.py        # Milvus connection & search
│   ├── test_neo4j_connection.py    # Connection testing
│   └── diagnose_neo4j.py       # Database diagnostics
│
├── query_engine/               # Query processing
│   ├── query_parser.py         # Parse user queries
│   ├── retriever.py            # Retrieve from databases
│   └── response_builder.py     # Build LLM responses
│
├── utils/                      # Utility modules
│   ├── embeddings.py           # Embedding generation (BGE-M3)
│   └── pdf_processor.py        # PDF text extraction
│
└── docs/                       # Documentation
    ├── setup/                  # Database setup guides
    │   ├── NEO4J_SETUP.md      # Neo4j installation
    │   ├── MILVUS_SETUP.md     # Milvus installation
    │   └── ATTU_SETUP.md       # Attu (Milvus UI) setup
    │
    ├── guides/                 # User guides
    │   ├── TESTING_GUIDE.md            # Testing procedures
    │   ├── VALIDATION_CHECKLIST.md     # Validation protocols
    │   └── PDF_DETAIL_FORMAT.md        # PDF response formats
    │
    └── implementation/         # Implementation details
        ├── ANTI_HALLUCINATION_MEASURES.md  # Anti-hallucination safeguards
        ├── FIXES_APPLIED.md                # Bug fixes & solutions
        └── UI_FORMATTING_CHANGES.md        # UI/UX improvements
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

## Documentation

### Setup Guides
- **[Neo4j Setup](docs/setup/NEO4J_SETUP.md)** - Install and configure Neo4j
- **[Milvus Setup](docs/setup/MILVUS_SETUP.md)** - Install and configure Milvus
- **[Attu Setup](docs/setup/ATTU_SETUP.md)** - Milvus web UI configuration

### User Guides
- **[Testing Guide](docs/guides/TESTING_GUIDE.md)** - Test PDF retrieval functionality
- **[Validation Checklist](docs/guides/VALIDATION_CHECKLIST.md)** - Validate system accuracy
- **[PDF Detail Format](docs/guides/PDF_DETAIL_FORMAT.md)** - PDF response formatting

### Implementation Details
- **[Anti-Hallucination Measures](docs/implementation/ANTI_HALLUCINATION_MEASURES.md)** - LLM accuracy safeguards
- **[Fixes Applied](docs/implementation/FIXES_APPLIED.md)** - Bug fixes and solutions
- **[UI Formatting Changes](docs/implementation/UI_FORMATTING_CHANGES.md)** - UI/UX improvements

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
- ✅ PDF to Milvus ingestion (Phase 2 Complete!)
- ⏳ Chat interface
- ⏳ Query engine

## Phase 2: PDF Processing Pipeline

The system now automatically processes PDFs when ingesting CSV data:

1. **Extracts unique PDF URLs** from CSV
2. **Downloads PDFs** (only once per unique URL)
3. **Extracts text** using pdfplumber
4. **Chunks text** into 500-1000 token pieces with overlap
5. **Generates embeddings** using BGE-M3 (free, 1024-dimensional)
6. **Stores in Milvus** with metadata:
   - Parts Town #
   - Manufacturer #
   - PDF URL
   - Page number
   - Chunk index

**Setup Milvus:**
1. Install Milvus: https://milvus.io/docs/install_standalone-docker.md
2. Start Milvus: `docker-compose up -d` (or use Milvus Lite)
3. Update `.env` with Milvus connection (optional):
   ```
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   ```

PDF processing runs **in parallel** with Neo4j ingestion for efficiency!

