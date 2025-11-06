"""
Main Streamlit application for CSV RAG Chat App.
"""
import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Find .env file in project root
project_root = Path(__file__).parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Add project root to path (already defined above)
sys.path.append(str(project_root))

from data_ingestion.csv_to_neo4j import CSVToNeo4j
from database.neo4j_client import Neo4jClient


st.set_page_config(
    page_title="CSV RAG Chat App",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 Partstown Trane Parts - CSV RAG Chat App")

# Initialize session state
if 'neo4j_client' not in st.session_state:
    st.session_state.neo4j_client = None
    st.session_state.data_loaded = False
    st.session_state.connection_error = None
    st.session_state.connection_attempted = False

# Automatically connect to Neo4j on startup using environment variables (only once)
if not st.session_state.connection_attempted:
    st.session_state.connection_attempted = True
    try:
        # Connect using environment variables only
        st.session_state.neo4j_client = Neo4jClient()
        st.session_state.connection_error = None
    except Exception as e:
        st.session_state.connection_error = str(e)
        st.session_state.neo4j_client = None

# Sidebar for CSV upload
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Show Neo4j connection status
    st.subheader("📊 Connection Status")
    if st.session_state.neo4j_client is not None:
        st.success("✅ Neo4j Connected")
        st.caption("Using credentials from .env file")
    else:
        st.error("❌ Neo4j Connection Failed")
        if st.session_state.connection_error:
            st.error(f"**Error:** {st.session_state.connection_error}")
            st.caption("Please check your .env file configuration")
    
    st.divider()
    
    # CSV upload section
    st.subheader("📁 CSV Upload")
    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=['csv'],
        help="Upload the CSV file containing parts and models data"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✓ File uploaded: {uploaded_file.name}")
        
        # Preview CSV
        try:
            df = pd.read_csv(temp_path)
            st.write(f"**Preview:** {len(df)} rows, {len(df.columns)} columns")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Store CSV path in session state
            st.session_state.csv_path = temp_path
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            temp_path = None
        
        # Ingest button
        if temp_path:
            if st.session_state.neo4j_client is not None:
                clear_existing = st.checkbox("Clear existing data before ingestion", value=False)
                
                if st.button("🚀 Ingest CSV into Neo4j"):
                    with st.spinner("Ingesting CSV data into Neo4j..."):
                        try:
                            converter = CSVToNeo4j(st.session_state.neo4j_client)
                            converter.ingest_csv(temp_path, clear_existing=clear_existing)
                            st.session_state.data_loaded = True
                            st.success("✓ CSV data successfully ingested into Neo4j!")
                            
                            # Get database stats
                            try:
                                stats = st.session_state.neo4j_client.get_database_stats()
                                st.info(f"""
                                **Ingestion Summary:**
                                - Models processed: {len(converter.processed_models)}
                                - Parts processed: {len(converter.processed_parts)}
                                - PDFs processed: {len(converter.processed_pdfs)}
                                
                                **Database Verification:**
                                - Total nodes in database: {stats['total_nodes']}
                                - Total relationships: {stats['total_relationships']}
                                """)
                                if stats['by_label']:
                                    st.json(stats['by_label'])
                            except Exception as stats_error:
                                st.warning(f"Could not verify database stats: {stats_error}")
                                st.info(f"""
                                **Ingestion Summary:**
                                - Models: {len(converter.processed_models)}
                                - Parts: {len(converter.processed_parts)}
                                - PDFs: {len(converter.processed_pdfs)}
                                """)
                        except Exception as e:
                            st.error(f"✗ Ingestion failed: {e}")
                            st.exception(e)
            else:
                st.warning("⚠️ Cannot ingest: Neo4j connection failed. Please check your .env file.")

# Main content area
if st.session_state.neo4j_client is None:
    st.error("❌ **Neo4j Connection Failed**")
    st.markdown("""
    Please check your `.env` file configuration:
    - Ensure `.env` file exists in the project root
    - Verify `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` are set correctly
    - Make sure your Neo4j instance is running
    
    **Error Details:** See sidebar for more information.
    """)
elif not st.session_state.data_loaded:
    st.info("📁 **Ready to upload CSV**")
    st.markdown("""
    Please upload a CSV file in the sidebar to begin ingesting data into Neo4j.
    
    Once the data is ingested, you'll be able to query it using the chat interface.
    """)
else:
    st.success("✅ **System Ready!**")
    st.markdown("""
    Your CSV data has been successfully ingested into Neo4j. 
    You can now query the data using the chat interface.
    """)
    
    # Placeholder for future chat interface
    st.subheader("💬 Chat Interface")
    st.write("Chat interface will be implemented in the next steps...")

