"""
FAISS vector store implementation for document retrieval
"""
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from langchain.schema import Document
from langchain.vectorstores import FAISS
from loguru import logger
import pickle

from src.embeddings import LangChainEmbeddings, EmbeddingGenerator
from config import settings


class VectorStore:
    """FAISS-based vector store for document retrieval"""
    
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator = None,
        index_path: Optional[Path] = None
    ):
        """
        Initialize vector store
        
        Args:
            embedding_generator: EmbeddingGenerator instance
            index_path: Path to save/load FAISS index
        """
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.embeddings = LangChainEmbeddings(self.embedding_generator)
        self.index_path = Path(index_path) if index_path else Path(settings.FAISS_INDEX_PATH)
        self.vectorstore: Optional[FAISS] = None
        
        logger.info(f"Initialized VectorStore with index path: {self.index_path}")
    
    def create_index(
        self, 
        documents: List[Document],
        save: bool = True
    ):
        """
        Create FAISS index from documents
        
        Args:
            documents: List of Document objects
            save: Save index to disk
        """
        logger.info(f"Creating FAISS index from {len(documents)} documents...")
        
        # Create FAISS vectorstore
        self.vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings
        )
        
        logger.info(
            f"Created FAISS index with {self.vectorstore.index.ntotal} vectors"
        )
        
        if save:
            self.save_index()
    
    def save_index(self):
        """Save FAISS index to disk"""
        if self.vectorstore is None:
            raise ValueError("No index to save. Create index first.")
        
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        self.vectorstore.save_local(str(self.index_path))
        
        logger.info(f"Saved FAISS index to {self.index_path}")
    
    def load_index(self):
        """Load FAISS index from disk"""
        if not self.index_path.exists():
            raise ValueError(f"Index not found at {self.index_path}")
        
        logger.info(f"Loading FAISS index from {self.index_path}")
        
        # Load FAISS index
        self.vectorstore = FAISS.load_local(
            str(self.index_path),
            embeddings=self.embeddings,
            allow_dangerous_deserialization=True  # Required for pickle
        )
        
        logger.info(
            f"Loaded FAISS index with {self.vectorstore.index.ntotal} vectors"
        )
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Search for similar documents
        
        Args:
            query: Query text
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of similar documents
        """
        if self.vectorstore is None:
            raise ValueError("No index loaded. Load or create index first.")
        
        results = self.vectorstore.similarity_search(
            query=query,
            k=k
        )
        
        return results
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents with similarity scores
        
        Args:
            query: Query text
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of (document, score) tuples
        """
        if self.vectorstore is None:
            raise ValueError("No index loaded. Load or create index first.")
        
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k
        )
        
        # Filter by score threshold if provided
        if score_threshold is not None:
            results = [
                (doc, score) 
                for doc, score in results 
                if score >= score_threshold
            ]
        
        return results
    
    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[Document]:
        """
        Search using Maximum Marginal Relevance (MMR)
        Balances relevance with diversity
        
        Args:
            query: Query text
            k: Number of results to return
            fetch_k: Number of candidates to fetch
            lambda_mult: Diversity parameter (0=max diversity, 1=max relevance)
            
        Returns:
            List of diverse, relevant documents
        """
        if self.vectorstore is None:
            raise ValueError("No index loaded. Load or create index first.")
        
        results = self.vectorstore.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult
        )
        
        return results
    
    def add_documents(
        self, 
        documents: List[Document],
        save: bool = True
    ):
        """
        Add new documents to existing index
        
        Args:
            documents: List of new Document objects
            save: Save updated index
        """
        if self.vectorstore is None:
            raise ValueError("No index loaded. Create index first.")
        
        self.vectorstore.add_documents(documents)
        
        logger.info(
            f"Added {len(documents)} documents. "
            f"Total vectors: {self.vectorstore.index.ntotal}"
        )
        
        if save:
            self.save_index()
    
    def delete_documents(
        self, 
        doc_ids: List[str],
        save: bool = True
    ):
        """
        Delete documents from index by IDs
        
        Args:
            doc_ids: List of document IDs to delete
            save: Save updated index
        """
        if self.vectorstore is None:
            raise ValueError("No index loaded. Load or create index first.")
        
        self.vectorstore.delete(doc_ids)
        
        logger.info(f"Deleted {len(doc_ids)} documents from index")
        
        if save:
            self.save_index()
    
    def get_statistics(self) -> dict:
        """
        Get index statistics
        
        Returns:
            Dictionary with index statistics
        """
        if self.vectorstore is None:
            return {"status": "No index loaded"}
        
        return {
            "total_vectors": self.vectorstore.index.ntotal,
            "embedding_dimension": self.embedding_generator.get_embedding_dim(),
            "index_type": type(self.vectorstore.index).__name__,
            "index_path": str(self.index_path)
        }


def create_optimized_index(
    documents: List[Document],
    embedding_generator: EmbeddingGenerator,
    use_gpu: bool = False
) -> faiss.Index:
    """
    Create optimized FAISS index for large-scale retrieval
    
    Args:
        documents: List of documents
        embedding_generator: EmbeddingGenerator instance
        use_gpu: Use GPU acceleration
        
    Returns:
        Optimized FAISS index
    """
    # Generate embeddings
    texts = [doc.page_content for doc in documents]
    embeddings = embedding_generator.embed_documents(texts)
    
    dimension = embeddings.shape[1]
    n_vectors = embeddings.shape[0]
    
    logger.info(
        f"Creating optimized index for {n_vectors} vectors "
        f"with dimension {dimension}"
    )
    
    # Choose index type based on dataset size
    if n_vectors < 10000:
        # Small dataset: use flat index
        index = faiss.IndexFlatIP(dimension)  # Inner product (cosine)
    else:
        # Large dataset: use IVF index with clustering
        n_clusters = min(int(np.sqrt(n_vectors)), 1000)
        quantizer = faiss.IndexFlatIP(dimension)
        index = faiss.IndexIVFFlat(
            quantizer, 
            dimension, 
            n_clusters,
            faiss.METRIC_INNER_PRODUCT
        )
        
        # Train index
        logger.info(f"Training IVF index with {n_clusters} clusters...")
        index.train(embeddings)
    
    # Move to GPU if requested
    if use_gpu and faiss.get_num_gpus() > 0:
        logger.info("Moving index to GPU...")
        index = faiss.index_cpu_to_gpu(
            faiss.StandardGpuResources(), 
            0, 
            index
        )
    
    # Add vectors
    index.add(embeddings)
    
    logger.info(f"Created index with {index.ntotal} vectors")
    
    return index
