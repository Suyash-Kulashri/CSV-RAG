"""
PDF to Milvus ingestion module.
Orchestrates the complete pipeline: download -> extract -> chunk -> embed -> store.
"""
import pandas as pd
from pathlib import Path
from typing import Set, Dict, List, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.pdf_downloader import PDFDownloader
from utils.pdf_processor import PDFProcessor
from utils.embeddings import EmbeddingGenerator
from database.milvus_client import MilvusClient


class PDFToMilvus:
    """Handle PDF processing and ingestion into Milvus."""
    
    def __init__(self, milvus_client: MilvusClient = None):
        """
        Initialize PDF to Milvus processor.
        
        Args:
            milvus_client: Milvus client instance (creates new if None)
        """
        self.milvus_client = milvus_client or MilvusClient()
        self.pdf_downloader = PDFDownloader()
        self.pdf_processor = PDFProcessor(chunk_size=800, chunk_overlap=100)
        self.embedding_generator = EmbeddingGenerator()
        
        self.processed_pdfs: Set[str] = set()
        self.total_chunks_processed = 0
    
    def extract_unique_pdf_urls(self, csv_path: str) -> Set[str]:
        """
        Extract unique PDF URLs from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Set of unique PDF URLs
        """
        df = pd.read_csv(csv_path)
        pdf_urls = set()
        
        # Check all columns for PDF links
        for col in df.columns:
            if col.startswith('PDF Link') or 'PDF' in col:
                urls = df[col].dropna().unique()
                for url in urls:
                    url_str = str(url).strip()
                    if url_str and url_str.lower().startswith('http'):
                        pdf_urls.add(url_str)
        
        return pdf_urls
    
    def process_pdf_to_milvus(self, 
                              pdf_url: str,
                              parts_town_number: str,
                              manufacturer_number: str,
                              pdf_path: Path = None):
        """
        Process a single PDF and store in Milvus.
        
        Args:
            pdf_url: URL of the PDF
            parts_town_number: Parts Town # identifier
            manufacturer_number: Manufacturer # identifier
            pdf_path: Optional path to already downloaded PDF
        """
        if pdf_url in self.processed_pdfs:
            return  # Already processed
        
        try:
            # Download PDF if not provided
            if pdf_path is None:
                pdf_path = self.pdf_downloader.download_pdf(pdf_url)
            
            # Prepare base metadata
            metadata = {
                'parts_town_number': parts_town_number or '',
                'manufacturer_number': manufacturer_number or '',
                'pdf_url': pdf_url
            }
            
            # Process PDF: extract and chunk
            chunks = self.pdf_processor.process_pdf(pdf_path, metadata)
            
            if not chunks:
                print(f"  ⚠️  No text extracted from PDF: {pdf_url}")
                return
            
            # Generate embeddings for all chunks
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings(texts)
            
            # Insert into Milvus
            self.milvus_client.insert_chunks(chunks, embeddings)
            
            self.processed_pdfs.add(pdf_url)
            self.total_chunks_processed += len(chunks)
            
            print(f"  ✓ Processed PDF: {len(chunks)} chunks from {pdf_url}")
            
        except Exception as e:
            print(f"  ✗ Error processing PDF {pdf_url}: {e}")
            raise
    
    def process_csv_pdfs(self, csv_path: str, df: pd.DataFrame = None):
        """
        Process all PDFs from CSV file.
        
        Args:
            csv_path: Path to CSV file
            df: Optional DataFrame (if already loaded)
        """
        if df is None:
            df = pd.read_csv(csv_path)
        
        print("\n📄 Processing PDFs from CSV...")
        
        # Extract unique PDF URLs with their associated part info
        # A PDF can be associated with multiple parts, so we store lists
        pdf_info_map: Dict[str, List[Dict]] = {}
        
        for _, row in df.iterrows():
            # Get Parts Town # and Manufacturer #
            parts_town_number = str(row.get('Parts Town #', '')).strip()
            if not parts_town_number:
                # Fallback to Part description if Parts Town # is missing
                parts_town_number = str(row.get('Part', '')).strip()
            manufacturer_number = str(row.get('Manufacturer #', '')).strip()
            
            # Check all columns for PDF links
            for col in df.columns:
                if col.startswith('PDF Link') or 'PDF' in col:
                    pdf_url = str(row.get(col, '')).strip()
                    if pdf_url and pdf_url.lower().startswith('http'):
                        if pdf_url not in pdf_info_map:
                            pdf_info_map[pdf_url] = []
                        
                        # Add part info for this PDF
                        pdf_info_map[pdf_url].append({
                            'parts_town_number': parts_town_number,
                            'manufacturer_number': manufacturer_number
                        })
        
        print(f"  Found {len(pdf_info_map)} unique PDF URLs")
        
        if not pdf_info_map:
            print("  ℹ️  No PDF URLs found in CSV")
            return
        
        # Download all PDFs first
        print("\n📥 Downloading PDFs...")
        downloaded_pdfs = self.pdf_downloader.download_pdfs_batch(set(pdf_info_map.keys()))
        
        # Process each PDF
        # For PDFs associated with multiple parts, we'll use the first part's info as primary
        # but all parts will be searchable via the parts_town_number field
        print("\n🔄 Processing PDFs (extract, chunk, embed, store)...")
        for pdf_url, part_info_list in pdf_info_map.items():
            if pdf_url in downloaded_pdfs:
                try:
                    # Use first part's info as primary metadata
                    primary_info = part_info_list[0]
                    
                    # Process PDF (chunks will be stored with metadata)
                    self.process_pdf_to_milvus(
                        pdf_url=pdf_url,
                        parts_town_number=primary_info['parts_town_number'],
                        manufacturer_number=primary_info['manufacturer_number'],
                        pdf_path=downloaded_pdfs[pdf_url]
                    )
                except Exception as e:
                    print(f"  ✗ Failed to process {pdf_url}: {e}")
                    continue
        
        # Print summary
        stats = self.pdf_downloader.get_stats()
        print(f"\n✓ PDF Processing Complete!")
        print(f"  - PDFs processed: {len(self.processed_pdfs)}")
        print(f"  - Total chunks: {self.total_chunks_processed}")
        print(f"  - PDFs downloaded: {stats['downloaded_count']}")
        if stats['failed_count'] > 0:
            print(f"  - Failed downloads: {stats['failed_count']}")
