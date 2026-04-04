"""
Embedding generation module using bge-small-en-v1.5
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from loguru import logger
import torch
from config import settings


class EmbeddingGenerator:
    """Generate embeddings for text using BGE model"""
    
    def __init__(
        self,
        model_name: str = None,
        device: str = None
    ):
        """
        Initialize embedding generator
        
        Args:
            model_name: HuggingFace model name (default: bge-small-en-v1.5)
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        
        # Auto-detect device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        
        logger.info(f"Loading embedding model: {self.model_name} on {device}")
        
        # Load model
        self.model = SentenceTransformer(self.model_name, device=device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        logger.info(
            f"Loaded {self.model_name} with dimension {self.embedding_dim}"
        )
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector as numpy array
        """
        # BGE models benefit from instruction prefix for queries
        query_with_instruction = f"Represent this sentence for searching relevant passages: {query}"
        
        embedding = self.model.encode(
            query_with_instruction,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        return embedding
    
    def embed_documents(
        self, 
        documents: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple documents
        
        Args:
            documents: List of document texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            
        Returns:
            Array of embeddings (n_docs, embedding_dim)
        """
        # No instruction prefix for documents
        embeddings = self.model.encode(
            documents,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        logger.info(f"Generated embeddings for {len(documents)} documents")
        
        return embeddings
    
    def get_embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        return np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )


class LangChainEmbeddings:
    """
    Wrapper for LangChain compatibility
    Implements LangChain's Embeddings interface
    """
    
    def __init__(self, embedding_generator: EmbeddingGenerator = None):
        """
        Initialize LangChain-compatible embeddings
        
        Args:
            embedding_generator: EmbeddingGenerator instance
        """
        self.generator = embedding_generator or EmbeddingGenerator()
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text
        
        Args:
            text: Query text
            
        Returns:
            Embedding as list of floats
        """
        embedding = self.generator.embed_query(text)
        return embedding.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embeddings
        """
        embeddings = self.generator.embed_documents(texts)
        return embeddings.tolist()
