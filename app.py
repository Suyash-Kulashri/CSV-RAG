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
from query_engine.query_parser import QueryParser
from query_engine.retriever import Retriever
from query_engine.response_builder import ResponseBuilder
from utils.embeddings import EmbeddingGenerator


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
    st.session_state.query_parser = None
    st.session_state.retriever = None
    st.session_state.response_builder = None
    st.session_state.conversation_history = []  # Buffer memory for conversation
    st.session_state.databases_checked = False
    st.session_state.databases_have_data = False

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
    
    # Initialize query engine components if databases are connected
    if st.session_state.neo4j_client:
        try:
            st.session_state.query_parser = QueryParser()
            # Initialize retriever with embedding generator if Milvus is available
            embedding_gen = None
            if st.session_state.milvus_client:
                embedding_gen = EmbeddingGenerator()
            st.session_state.retriever = Retriever(
                neo4j_client=st.session_state.neo4j_client,
                milvus_client=st.session_state.milvus_client,
                embedding_generator=embedding_gen
            )
            st.session_state.response_builder = ResponseBuilder()
        except Exception as e:
            st.warning(f"Could not initialize query engine: {e}")
    
    # Check if databases have data (only once)
    if not st.session_state.databases_checked and st.session_state.neo4j_client:
        try:
            neo4j_stats = st.session_state.neo4j_client.get_database_stats()
            neo4j_has_data = neo4j_stats.get('total_nodes', 0) > 0
            
            milvus_has_data = False
            if st.session_state.milvus_client:
                try:
                    milvus_stats = st.session_state.milvus_client.get_collection_stats()
                    milvus_has_data = milvus_stats.get('entity_count', 0) > 0
                except:
                    milvus_has_data = False
            
            # Databases have data if Neo4j has nodes (Milvus is optional)
            st.session_state.databases_have_data = neo4j_has_data
            st.session_state.databases_checked = True
        except Exception as e:
            st.session_state.databases_have_data = False
            st.session_state.databases_checked = True

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
                
                if st.button("📤 Upload"):
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
                            st.session_state.databases_have_data = True  # Update flag after ingestion
                            st.session_state.databases_checked = True
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
elif not st.session_state.databases_have_data:
    # Databases are empty - show upload prompt
    st.info("📁 **Databases are Empty - Upload CSV Required**")
    st.markdown("""
    Your Neo4j and Milvus databases are currently empty. 
    
    **To get started:**
    1. Upload a CSV file in the sidebar
    2. Click "🚀 Ingest CSV into Neo4j" to load data
    3. Once data is ingested, you'll be able to query it using the chat interface
    
    **Note:** If you've already ingested data before, make sure your databases are running and accessible.
    """)
    
    # Show database status
    with st.expander("📊 Current Database Status", expanded=True):
        try:
            neo4j_stats = st.session_state.neo4j_client.get_database_stats()
            st.write(f"**Neo4j:** {neo4j_stats.get('total_nodes', 0)} nodes")
            if st.session_state.milvus_client:
                try:
                    milvus_stats = st.session_state.milvus_client.get_collection_stats()
                    st.write(f"**Milvus:** {milvus_stats.get('entity_count', 0)} chunks")
                except:
                    st.write("**Milvus:** Not available")
        except:
            st.write("**Status:** Unable to check")
else:
    # Databases have data - show chat interface
    st.success("✅ **System Ready!**")
    
    # Show database stats
    with st.expander("📊 Database Status", expanded=False):
        try:
            neo4j_stats = st.session_state.neo4j_client.get_database_stats()
            st.write(f"**Neo4j:** {neo4j_stats.get('total_nodes', 0)} nodes, {neo4j_stats.get('total_relationships', 0)} relationships")
            if neo4j_stats.get('by_label'):
                st.write("**Nodes by type:**")
                for label, count in neo4j_stats['by_label'].items():
                    st.write(f"  - {label}: {count}")
            
            if st.session_state.milvus_client:
                try:
                    milvus_stats = st.session_state.milvus_client.get_collection_stats()
                    st.write(f"**Milvus:** {milvus_stats.get('entity_count', 0)} PDF chunks")
                except:
                    st.write("**Milvus:** Not available")
        except Exception as e:
            st.write(f"Could not retrieve stats: {e}")
    
    # Chat Interface
    st.subheader("💬 Chat Interface")
    st.markdown("Ask questions about parts, models, or equipment. The system will search both structured data and PDF manuals.")
    
    # Display conversation history
    if st.session_state.conversation_history:
        st.markdown("### Conversation History")
        for i, message in enumerate(st.session_state.conversation_history):
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'user':
                with st.chat_message("user"):
                    st.write(content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(content)
                    # PDF URLs are now integrated within the response text itself
                    # No separate PDF URLs section displayed
    
    # Chat input
    user_query = st.chat_input("Ask a question about parts or models...")
    
    if user_query:
        # Add user message to history
        st.session_state.conversation_history.append({
            'role': 'user',
            'content': user_query
        })
        
        # Process query
        if st.session_state.query_parser and st.session_state.retriever and st.session_state.response_builder:
            with st.spinner("Processing your query..."):
                try:
                    print(f"\n{'='*60}")
                    print(f"USER QUERY: {user_query}")
                    print(f"{'='*60}")
                    
                    # Parse query
                    parsed_query = st.session_state.query_parser.parse(user_query)
                    print(f"\nParsed Query:")
                    print(f"  Intent: {parsed_query.get('intent')}")
                    print(f"  Parts: {parsed_query.get('parts_town_numbers')}")
                    print(f"  Models: {parsed_query.get('model_names')}")
                    
                    # Retrieve data
                    retrieval_results = st.session_state.retriever.retrieve(
                        parsed_query,
                        top_k=5,
                        similarity_threshold=0.7
                    )
                    
                    print(f"\nRetrieval Results:")
                    print(f"  Neo4j parts: {len(retrieval_results.get('neo4j_results', {}).get('parts', []))}")
                    print(f"  Neo4j models: {len(retrieval_results.get('neo4j_results', {}).get('models', []))}")
                    print(f"  Milvus chunks: {len(retrieval_results.get('milvus_results', []))}")
                    
                    # Get context and metadata for streaming
                    neo4j_results = retrieval_results.get('neo4j_results', {})
                    milvus_results = retrieval_results.get('milvus_results', [])
                    query_intent = retrieval_results.get('query_intent', 'general')
                    
                    context = st.session_state.response_builder._build_context(neo4j_results, milvus_results)
                    
                    # Stream the response in real-time
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        # Get streaming generator
                        stream_generator = st.session_state.response_builder.generate_streaming_response(
                            user_query=user_query,
                            context=context,
                            conversation_history=st.session_state.conversation_history[:-1],
                            query_intent=query_intent
                        )
                        
                        # Stream the response word by word
                        for chunk in stream_generator:
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")  # Cursor effect
                        
                        # Final response without cursor
                        response_placeholder.markdown(full_response)
                    
                    # Extract PDF URLs
                    pdf_urls = st.session_state.response_builder._extract_relevant_pdf_urls(
                        neo4j_results, milvus_results, query_intent
                    )
                    
                    print(f"\nResponse completed:")
                    print(f"  PDF URLs: {len(pdf_urls)}")
                    print(f"{'='*60}\n")
                    
                    # Add assistant response to history
                    st.session_state.conversation_history.append({
                        'role': 'assistant',
                        'content': full_response,
                        'pdf_urls': pdf_urls,
                        'sources': []
                    })
                    
                    # Force rerun to update the display
                    st.rerun()
                    
                except Exception as e:
                    error_msg = f"I encountered an error processing your query: {str(e)}"
                    st.session_state.conversation_history.append({
                        'role': 'assistant',
                        'content': error_msg
                    })
                    st.error(error_msg)
                    st.exception(e)
                    st.rerun()
        else:
            st.error("Query engine not initialized. Please check your database connections.")
    
    # Clear conversation button
    if st.session_state.conversation_history:
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation_history = []
            st.rerun()

