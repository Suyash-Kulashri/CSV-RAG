"""
PDF downloader module for downloading unique PDFs from URLs.
"""
import requests
import os
from pathlib import Path
from typing import Set, Dict
from tqdm import tqdm
import hashlib


class PDFDownloader:
    """Handle downloading PDFs from URLs."""
    
    def __init__(self, download_dir: str = "downloaded_pdfs"):
        """
        Initialize PDF downloader.
        
        Args:
            download_dir: Directory to save downloaded PDFs
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.downloaded_urls: Set[str] = set()
        self.failed_downloads: Dict[str, str] = {}
    
    def get_pdf_filename(self, url: str) -> str:
        """
        Generate a filename for PDF based on URL.
        
        Args:
            url: PDF URL
            
        Returns:
            Filename for the PDF
        """
        # Use URL hash as filename to avoid issues with special characters
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{url_hash}.pdf"
    
    def download_pdf(self, url: str, timeout: int = 30) -> Path:
        """
        Download a PDF from URL.
        
        Args:
            url: PDF URL
            timeout: Request timeout in seconds
            
        Returns:
            Path to downloaded PDF file
            
        Raises:
            Exception: If download fails
        """
        if url in self.downloaded_urls:
            # Already downloaded, return existing path
            filename = self.get_pdf_filename(url)
            return self.download_dir / filename
        
        filename = self.get_pdf_filename(url)
        file_path = self.download_dir / filename
        
        # Skip if file already exists
        if file_path.exists():
            self.downloaded_urls.add(url)
            return file_path
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Check if content is actually a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                # Check first few bytes for PDF magic number
                first_bytes = response.content[:4]
                if first_bytes != b'%PDF':
                    raise ValueError(f"URL does not point to a PDF file: {content_type}")
            
            # Download and save
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.downloaded_urls.add(url)
            return file_path
            
        except Exception as e:
            self.failed_downloads[url] = str(e)
            if file_path.exists():
                file_path.unlink()  # Remove partial download
            raise
    
    def download_pdfs_batch(self, urls: Set[str], show_progress: bool = True) -> Dict[str, Path]:
        """
        Download multiple PDFs.
        
        Args:
            urls: Set of PDF URLs to download
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary mapping URLs to file paths
        """
        downloaded = {}
        urls_to_download = [url for url in urls if url not in self.downloaded_urls]
        
        if not urls_to_download:
            # All already downloaded
            for url in urls:
                filename = self.get_pdf_filename(url)
                downloaded[url] = self.download_dir / filename
            return downloaded
        
        iterator = tqdm(urls_to_download, desc="Downloading PDFs") if show_progress else urls_to_download
        
        for url in iterator:
            try:
                file_path = self.download_pdf(url)
                downloaded[url] = file_path
            except Exception as e:
                print(f"  ⚠️  Failed to download {url}: {e}")
                continue
        
        return downloaded
    
    def get_stats(self) -> Dict:
        """Get download statistics."""
        return {
            'downloaded_count': len(self.downloaded_urls),
            'failed_count': len(self.failed_downloads),
            'failed_urls': list(self.failed_downloads.keys())
        }
