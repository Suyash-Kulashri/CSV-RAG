"""
PDF text extraction and chunking utilities.
"""
import pdfplumber
from typing import List, Dict
from pathlib import Path
import re


class PDFProcessor:
    """Handle PDF text extraction and chunking."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        """
        Initialize PDF processor.
        
        Args:
            chunk_size: Target chunk size in tokens (approximate)
            chunk_overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, any]]:
        """
        Extract text from PDF with page information.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dictionaries with 'text' and 'page_number' keys
        """
        pages_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        # Clean up text
                        text = self._clean_text(text)
                        pages_text.append({
                            'text': text,
                            'page_number': page_num
                        })
        except Exception as e:
            raise Exception(f"Error extracting text from PDF {pdf_path}: {e}")
        
        return pages_text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate number of tokens in text (rough approximation).
        Uses word count * 1.3 as approximation for tokens.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        word_count = len(text.split())
        return int(word_count * 1.3)
    
    def chunk_text(self, text: str, page_number: int, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Chunk text into smaller pieces.
        
        Args:
            text: Text to chunk
            page_number: Page number for metadata
            metadata: Additional metadata to include in chunks
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        metadata = metadata or {}
        
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_metadata = {
                    **metadata,
                    'page_number': page_number,
                    'chunk_index': len(chunks),
                    'text_length': len(chunk_text),
                    'estimated_tokens': current_tokens
                }
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Keep last few sentences for overlap
                    overlap_tokens = 0
                    overlap_sentences = []
                    for s in reversed(current_chunk):
                        s_tokens = self._estimate_tokens(s)
                        if overlap_tokens + s_tokens <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_metadata = {
                **metadata,
                'page_number': page_number,
                'chunk_index': len(chunks),
                'text_length': len(chunk_text),
                'estimated_tokens': current_tokens
            }
            chunks.append({
                'text': chunk_text,
                'metadata': chunk_metadata
            })
        
        return chunks
    
    def process_pdf(self, pdf_path: Path, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Process PDF: extract text and chunk it.
        
        Args:
            pdf_path: Path to PDF file
            metadata: Base metadata to include in all chunks
            
        Returns:
            List of chunk dictionaries ready for embedding
        """
        all_chunks = []
        
        # Extract text from all pages
        pages_text = self.extract_text_from_pdf(pdf_path)
        
        # Chunk each page
        for page_data in pages_text:
            page_chunks = self.chunk_text(
                page_data['text'],
                page_data['page_number'],
                metadata
            )
            all_chunks.extend(page_chunks)
        
        return all_chunks
