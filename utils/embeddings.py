"""
Embedding utilities for generating vector embeddings using BGE-M3.
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
import torch
import platform


class EmbeddingGenerator:
    """Generate embeddings using BGE-M3 model."""
    
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of the BGE-M3 model
        """
        print(f"Loading embedding model: {model_name}...")
        
        # Disable MPS (Metal Performance Shaders) on macOS to avoid Metal array size limitations
        # Metal has a 2^32 byte limit which can be exceeded with large batches
        if platform.system() == "Darwin":
            print("  ⚠️  Using CPU on macOS to avoid Metal array size limitations")
            # Force CPU usage to avoid Metal issues
            self.device = 'cpu'
        else:
            # Use GPU if available, otherwise CPU
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.model = SentenceTransformer(model_name, device=self.device)
        self.model_name = model_name
        print(f"✓ Model loaded successfully (using {self.device})")
    
    def generate_embeddings(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            batch_size: Batch size for processing (reduced for large batches to avoid Metal limitations)
            
        Returns:
            Numpy array of embeddings (shape: [num_texts, embedding_dim])
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # Reduce batch size for very large batches to avoid memory/Metal issues
        # Metal has a 2^32 byte limit (~4GB), so we need smaller batches
        num_texts = len(texts)
        if num_texts > 1000:
            # For large batches, use smaller batch size
            batch_size = min(batch_size, 16)
        elif num_texts > 500:
            batch_size = min(batch_size, 24)
        
        # Process in chunks if batch is very large to avoid Metal array size issues
        max_chunk_size = 500  # Process max 500 texts at a time
        if num_texts > max_chunk_size:
            print(f"  Processing {num_texts} texts in chunks of {max_chunk_size}...")
            all_embeddings = []
            for i in range(0, num_texts, max_chunk_size):
                chunk_texts = texts[i:i + max_chunk_size]
                chunk_embeddings = self.model.encode(
                    chunk_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                all_embeddings.append(chunk_embeddings)
            embeddings = np.vstack(all_embeddings)
        else:
            # Generate embeddings for smaller batches
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True
            )
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        # BGE-M3 produces 1024-dimensional embeddings
        # But let's get it dynamically
        test_embedding = self.generate_embeddings("test")
        return test_embedding.shape[1]
