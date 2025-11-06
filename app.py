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
from data_ingestion.pdf_to_milvus import PDFToMilvus
from database.neo4j_client import Neo4jClient
from database.milvus_client import MilvusClient


st.set_page_config(
    page_title="CSV RAG Chat App",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 Partstown Trane Parts - CSV RAG Chat App")

# Initialize session state
if 'neo4j_client' not in st.session_state:
    st.session_state.neo4j_client = None
    st.session_state.milvus_client = None
    st.session_state.data_loaded = False
    st.session_state.connection_error = None
    st.session_state.connection_attempted = False

# Automatically connect to Neo4j and Milvus on startup using environment variables (only once)
if not st.session_state.connection_attempted:
    st.session_state.connection_attempted = True
    try:
        # Connect to Neo4j using environment variables only
        st.session_state.neo4j_client = Neo4jClient()
        st.session_state.connection_error = None
    except Exception as e:
        st.session_state.connection_error = str(e)
        st.session_state.neo4j_client = None
    
    # Try to connect to Milvus (optional, won't fail if not available)
    try:
        st.session_state.milvus_client = MilvusClient()
    except Exception as e:
        st.session_state.milvus_client = None
        # Don't set error, Milvus is optional

# Sidebar for CSV upload
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Show connection status
    st.subheader("📊 Connection Status")
    
    # Neo4j status
    if st.session_state.neo4j_client is not None:
        st.success("✅ Neo4j Connected")
    else:
        st.error("❌ Neo4j Connection Failed")
        if st.session_state.connection_error:
            st.error(f"**Error:** {st.session_state.connection_error}")
    
    # Milvus status
    if st.session_state.milvus_client is not None:
        st.success("✅ Milvus Connected")
    else:
        st.warning("⚠️ Milvus Not Connected (PDF processing disabled)")
    
    st.caption("Using credentials from .env file")
    
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
                    with st.spinner("Ingesting CSV data into Neo4j and processing PDFs..."):
                        try:
                            # Initialize PDF processor if Milvus is available
                            pdf_processor = None
                            if st.session_state.milvus_client:
                                pdf_processor = PDFToMilvus(milvus_client=st.session_state.milvus_client)
                            
                            converter = CSVToNeo4j(
                                st.session_state.neo4j_client,
                                pdf_processor=pdf_processor
                            )
                            converter.ingest_csv(
                                temp_path, 
                                clear_existing=clear_existing,
                                process_pdfs=(pdf_processor is not None)
                            )
                            st.session_state.data_loaded = True
                            st.success("✓ CSV data successfully ingested into Neo4j!")
                            
                            # Get database stats
                            summary_text = f"""
                            **Neo4j Ingestion Summary:**
                            - Models processed: {len(converter.processed_models)}
                            - Parts processed: {len(converter.processed_parts)}
                            - PDFs linked: {len(converter.processed_pdfs)}
                            """
                            
                            try:
                                neo4j_stats = st.session_state.neo4j_client.get_database_stats()
                                summary_text += f"""
                                
                                **Neo4j Database:**
                                - Total nodes: {neo4j_stats['total_nodes']}
                                - Total relationships: {neo4j_stats['total_relationships']}
                                """
                                if neo4j_stats.get('by_label'):
                                    summary_text += "\n- Nodes by label:"
                                    for label, count in neo4j_stats['by_label'].items():
                                        summary_text += f"\n  - {label}: {count}"
                            except Exception as stats_error:
                                st.warning(f"Could not verify Neo4j stats: {stats_error}")
                            
                            # Get Milvus stats if PDF processing was enabled
                            if pdf_processor:
                                try:
                                    milvus_stats = st.session_state.milvus_client.get_collection_stats()
                                    summary_text += f"""
                                    
                                    **Milvus (PDF Processing):**
                                    - PDFs processed: {len(pdf_processor.processed_pdfs)}
                                    - Chunks stored: {milvus_stats.get('entity_count', 0)}
                                    """
                                except Exception as milvus_error:
                                    summary_text += f"\n\n⚠️ Could not get Milvus stats: {milvus_error}"
                            
                            st.info(summary_text)
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

