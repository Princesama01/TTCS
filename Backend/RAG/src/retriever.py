"""
Advanced retrieval module with Multi-query Retrieval and Cross-Encoder Reranking
"""
from typing import List, Tuple, Dict, Optional
from langchain.schema import Document
from sentence_transformers import CrossEncoder
from loguru import logger
import numpy as np

from src.vector_store import VectorStore
from config import settings


class MultiQueryRetriever:
    """
    Multi-query retrieval strategy
    Generates multiple query variations to improve recall
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        n_queries: int = 3
    ):
        """
        Initialize multi-query retriever
        
        Args:
            vector_store: VectorStore instance
            n_queries: Number of query variations to generate
        """
        self.vector_store = vector_store
        self.n_queries = n_queries
        
        logger.info(f"Initialized MultiQueryRetriever with {n_queries} queries")
    
    def generate_query_variations(self, query: str) -> List[str]:
        """
        Generate variations of the original query
        Simple rule-based approach (can be enhanced with LLM)
        
        Args:
            query: Original query
            
        Returns:
            List of query variations
        """
        variations = [query]  # Original query
        
        # Add question reformulations
        if "?" not in query:
            variations.append(f"{query}?")
        
        # Add contextual variations
        variations.append(f"Thông tin về {query}")
        variations.append(f"Chi tiết {query}")
        
        return variations[:self.n_queries]
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        deduplicate: bool = True
    ) -> List[Document]:
        """
        Retrieve documents using multiple query variations
        
        Args:
            query: Original query
            k: Number of documents to retrieve per query
            deduplicate: Remove duplicate documents
            
        Returns:
            List of retrieved documents
        """
        # Generate query variations
        queries = self.generate_query_variations(query)
        logger.info(f"Generated {len(queries)} query variations")
        
        # Retrieve documents for each query
        all_documents = []
        seen_contents = set()
        
        for q in queries:
            docs = self.vector_store.similarity_search(
                query=q,
                k=k
            )
            
            for doc in docs:
                if deduplicate:
                    # Deduplicate by content hash
                    content_hash = hash(doc.page_content)
                    if content_hash not in seen_contents:
                        seen_contents.add(content_hash)
                        all_documents.append(doc)
                else:
                    all_documents.append(doc)
        
        logger.info(
            f"Retrieved {len(all_documents)} unique documents "
            f"from {len(queries)} queries"
        )
        
        return all_documents


class CrossEncoderReranker:
    """
    Cross-Encoder reranking for improving retrieval precision
    """
    
    def __init__(
        self,
        model_name: str = None,
        device: str = None
    ):
        """
        Initialize cross-encoder reranker
        
        Args:
            model_name: HuggingFace model name (default: ms-marco-MiniLM-L-6-v2)
            device: Device to run model on
        """
        self.model_name = model_name or settings.RERANK_MODEL_NAME
        
        logger.info(f"Loading reranker model: {self.model_name}")
        
        # Load cross-encoder model
        self.model = CrossEncoder(self.model_name, device=device)
        
        logger.info(f"Loaded reranker: {self.model_name}")
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 3
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents using cross-encoder
        
        Args:
            query: Search query
            documents: List of retrieved documents
            top_k: Number of top documents to return
            
        Returns:
            List of (document, score) tuples, sorted by relevance
        """
        if not documents:
            return []
        
        # Prepare query-document pairs
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Get reranking scores
        scores = self.model.predict(pairs)
        
        # Sort documents by score
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Get top-k documents
        top_docs = doc_score_pairs[:top_k]
        
        logger.info(
            f"Reranked {len(documents)} documents, returning top {len(top_docs)}"
        )
        
        return top_docs
    
    def rerank_with_threshold(
        self,
        query: str,
        documents: List[Document],
        threshold: float = 0.5,
        top_k: Optional[int] = None
    ) -> List[Tuple[Document, float]]:
        """
        Rerank and filter documents by score threshold
        
        Args:
            query: Search query
            documents: List of retrieved documents
            threshold: Minimum score threshold
            top_k: Maximum number of documents to return (optional)
            
        Returns:
            List of (document, score) tuples above threshold
        """
        reranked = self.rerank(query, documents, top_k=len(documents))
        
        # Filter by threshold
        filtered = [
            (doc, score) 
            for doc, score in reranked 
            if score >= threshold
        ]
        
        # Apply top_k limit if specified
        if top_k:
            filtered = filtered[:top_k]
        
        logger.info(
            f"Filtered {len(filtered)} documents above threshold {threshold}"
        )
        
        return filtered


class AdvancedRetriever:
    """
    Complete retrieval pipeline with multi-query and reranking
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        use_multi_query: bool = True,
        use_reranking: bool = True,
        n_queries: int = 3,
        initial_k: int = 10,
        final_k: int = 3,
        rerank_threshold: Optional[float] = None
    ):
        """
        Initialize advanced retriever
        
        Args:
            vector_store: VectorStore instance
            use_multi_query: Use multi-query retrieval
            use_reranking: Use cross-encoder reranking
            n_queries: Number of query variations
            initial_k: Number of documents to retrieve initially
            final_k: Number of final documents after reranking
            rerank_threshold: Score threshold for reranking (optional)
        """
        self.vector_store = vector_store
        self.use_multi_query = use_multi_query
        self.use_reranking = use_reranking
        self.initial_k = initial_k
        self.final_k = final_k
        self.rerank_threshold = rerank_threshold
        
        # Initialize components
        if use_multi_query:
            self.multi_query_retriever = MultiQueryRetriever(
                vector_store=vector_store,
                n_queries=n_queries
            )
        
        if use_reranking:
            self.reranker = CrossEncoderReranker()
        
        logger.info(
            f"Initialized AdvancedRetriever: "
            f"multi_query={use_multi_query}, reranking={use_reranking}, "
            f"initial_k={initial_k}, final_k={final_k}"
        )
    
    def retrieve(
        self,
        query: str,
        return_scores: bool = False
    ) -> List[Document] | List[Tuple[Document, float]]:
        """
        Retrieve relevant documents using full pipeline
        
        Args:
            query: Search query
            return_scores: Return documents with scores
            
        Returns:
            List of relevant documents (with scores if requested)
        """
        # Stage 1: Initial retrieval
        if self.use_multi_query:
            documents = self.multi_query_retriever.retrieve(
                query=query,
                k=self.initial_k
            )
        else:
            documents = self.vector_store.similarity_search(
                query=query,
                k=self.initial_k
            )
        
        logger.info(f"Stage 1: Retrieved {len(documents)} documents")
        
        if not documents:
            return []
        
        # Stage 2: Reranking
        if self.use_reranking:
            if self.rerank_threshold is not None:
                reranked = self.reranker.rerank_with_threshold(
                    query=query,
                    documents=documents,
                    threshold=self.rerank_threshold,
                    top_k=self.final_k
                )
            else:
                reranked = self.reranker.rerank(
                    query=query,
                    documents=documents,
                    top_k=self.final_k
                )
            
            logger.info(f"Stage 2: Reranked to {len(reranked)} documents")
            
            if return_scores:
                return reranked
            else:
                return [doc for doc, _ in reranked]
        
        # No reranking: return initial results
        final_docs = documents[:self.final_k]
        
        if return_scores:
            # Get scores from vector store
            doc_scores = self.vector_store.similarity_search_with_score(
                query=query,
                k=self.final_k
            )
            return doc_scores
        
        return final_docs
    
    def get_context_string(
        self,
        query: str,
        separator: str = "\n\n---\n\n"
    ) -> str:
        """
        Get retrieved documents as a single context string
        
        Args:
            query: Search query
            separator: Separator between documents
            
        Returns:
            Concatenated context string
        """
        documents = self.retrieve(query, return_scores=False)
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            context_parts.append(
                f"[Document {i} - {source}, Page {page}]\n{doc.page_content}"
            )
        
        return separator.join(context_parts)
    
    def get_sources(
        self,
        query: str
    ) -> List[Dict]:
        """
        Get source metadata for retrieved documents
        
        Args:
            query: Search query
            
        Returns:
            List of source metadata dictionaries
        """
        documents = self.retrieve(query, return_scores=True)
        
        sources = []
        for doc, score in documents:
            sources.append({
                "filename": doc.metadata.get("filename", "Unknown"),
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A"),
                "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                "score": float(score),
                "preview": doc.page_content[:200] + "..."
            })
        
        return sources
