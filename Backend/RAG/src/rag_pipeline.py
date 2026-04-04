"""
Main RAG pipeline integrating all components
"""
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger
import time

from src.document_processor import PDFProcessor
from src.embeddings import EmbeddingGenerator
from src.vector_store import VectorStore
from src.retriever import AdvancedRetriever
from src.llm import LlamaLLM, create_rag_prompt, create_conversation_prompt
from config import settings


class RAGPipeline:
    """
    Complete RAG pipeline for document Q&A
    """
    
    def __init__(
        self,
        vector_store_path: Optional[Path] = None,
        load_existing: bool = True
    ):
        """
        Initialize RAG pipeline
        
        Args:
            vector_store_path: Path to vector store (default from settings)
            load_existing: Load existing vector store if available
        """
        logger.info("Initializing RAG Pipeline...")
        
        # Initialize components
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore(
            embedding_generator=self.embedding_generator,
            index_path=vector_store_path
        )
        
        # Load existing vector store if available
        if load_existing:
            try:
                self.vector_store.load_index()
                logger.info("✓ Loaded existing vector store")
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
                logger.info("Will create new index when documents are added")
        
        # Initialize retriever
        self.retriever = AdvancedRetriever(
            vector_store=self.vector_store,
            use_multi_query=True,
            use_reranking=True,
            initial_k=settings.TOP_K_RETRIEVAL,
            final_k=settings.TOP_K_RERANK,
            rerank_threshold=settings.SIMILARITY_THRESHOLD
        )
        
        # Initialize LLM
        self.llm = LlamaLLM()
        
        # Conversation history storage
        self.conversations: Dict[str, List[Dict]] = {}
        
        logger.info("✓ RAG Pipeline initialized successfully")
    
    def ingest_documents(
        self,
        pdf_directory: Path,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        save: bool = True
    ):
        """
        Ingest PDF documents into the system
        
        Args:
            pdf_directory: Directory containing PDF files
            chunk_size: Custom chunk size (default from settings)
            chunk_overlap: Custom chunk overlap (default from settings)
            save: Save vector store after ingestion
        """
        logger.info(f"Ingesting documents from: {pdf_directory}")
        
        # Initialize document processor
        processor = PDFProcessor(
            chunk_size=chunk_size or settings.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP
        )
        
        # Process all PDFs
        documents = processor.process_directory(pdf_directory)
        
        if not documents:
            logger.error("No documents to ingest")
            return
        
        # Create or update vector store
        try:
            # Try to add to existing index
            self.vector_store.add_documents(documents, save=save)
            logger.info("✓ Added documents to existing index")
        except:
            # Create new index
            self.vector_store.create_index(documents, save=save)
            logger.info("✓ Created new index with documents")
        
        logger.info(
            f"✓ Ingested {len(documents)} document chunks from "
            f"{len(list(Path(pdf_directory).glob('*.pdf')))} PDFs"
        )
    
    def query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        return_source_documents: bool = False,
        language: str = "vi"
    ) -> Dict:
        """
        Query the RAG system
        
        Args:
            question: User question
            conversation_id: ID for conversation tracking
            return_source_documents: Include source documents in response
            language: Response language ('vi' or 'en')
            
        Returns:
            Dictionary with answer and optional metadata
        """
        start_time = time.time()
        
        logger.info(f"Processing query: {question[:100]}...")
        
        # Stage 1: Retrieve relevant documents
        retrieval_start = time.time()
        retrieved_docs = self.retriever.retrieve(
            query=question,
            return_scores=return_source_documents
        )
        retrieval_time = time.time() - retrieval_start
        
        if not retrieved_docs:
            logger.warning("No relevant documents found")
            return {
                "answer": "Tôi không tìm thấy thông tin liên quan trong tài liệu." if language == "vi" 
                         else "I cannot find relevant information in the documents.",
                "source_documents": [],
                "retrieval_time": retrieval_time,
                "generation_time": 0,
                "total_time": time.time() - start_time
            }
        
        # Extract documents and scores
        if return_source_documents:
            documents = [doc for doc, _ in retrieved_docs]
            scores = [score for _, score in retrieved_docs]
        else:
            documents = retrieved_docs
            scores = []
        
        logger.info(f"✓ Retrieved {len(documents)} documents in {retrieval_time:.2f}s")
        
        # Stage 2: Build context
        context = self._build_context(documents)
        
        # Stage 3: Generate answer
        generation_start = time.time()
        
        # Get chat history if conversation_id provided
        chat_history = None
        if conversation_id:
            chat_history = self.conversations.get(conversation_id, [])
        
        # Create prompt
        if chat_history:
            prompt = create_conversation_prompt(
                question=question,
                context=context,
                chat_history=chat_history,
                language=language
            )
        else:
            prompt = create_rag_prompt(
                question=question,
                context=context,
                language=language
            )
        
        # Generate answer
        answer = self.llm.generate(
            prompt=prompt,
            stop=["<|eot_id|>", "<|end_of_text|>"]
        )
        
        generation_time = time.time() - generation_start
        total_time = time.time() - start_time
        
        logger.info(
            f"✓ Generated answer in {generation_time:.2f}s "
            f"(Total: {total_time:.2f}s)"
        )
        
        # Store conversation
        if conversation_id:
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            self.conversations[conversation_id].append({
                "question": question,
                "answer": answer
            })
        
        # Build response
        response = {
            "answer": answer.strip(),
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": total_time
        }
        
        if return_source_documents:
            response["source_documents"] = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": scores[i] if scores else None
                }
                for i, doc in enumerate(documents)
            ]
        
        return response
    
    def _build_context(
        self, 
        documents: List,
        max_context_length: int = 3000
    ) -> str:
        """
        Build context string from retrieved documents (Updated with Citation Engine logic)
        
        Args:
            documents: List of Document objects
            max_context_length: Maximum context length
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc.metadata.get("doc_id", "N/A")
            version = doc.metadata.get("version", "N/A")
            structure = doc.metadata.get("structure_path", doc.metadata.get("article", "N/A"))
            page = doc.metadata.get("page", "N/A")
            chunk_id = doc.metadata.get("chunk_id", "N/A")
            
            meta_header = f"[Doc {version} - {structure} | ID: {doc_id} | Page: {page} | Chunk: {chunk_id}]"
            doc_text = f"{meta_header}\n{doc.page_content}\n"
            
            # Check length limit
            if current_length + len(doc_text) > max_context_length:
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        return "\n\n".join(context_parts)
    
    def get_sources(self, question: str) -> List[Dict]:
        """
        Get source documents for a question
        
        Args:
            question: User question
            
        Returns:
            List of source metadata
        """
        return self.retriever.get_sources(question)
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")
    
    def get_statistics(self) -> Dict:
        """
        Get system statistics
        
        Returns:
            Dictionary with system stats
        """
        vector_stats = self.vector_store.get_statistics()
        llm_info = self.llm.get_model_info()
        
        return {
            "vector_store": vector_stats,
            "llm": llm_info,
            "active_conversations": len(self.conversations),
            "total_conversation_turns": sum(
                len(conv) for conv in self.conversations.values()
            )
        }


def quick_test():
    """Quick test of the RAG pipeline"""
    logger.info("Running quick test...")
    
    # Initialize pipeline
    rag = RAGPipeline(load_existing=False)
    
    # Test query (will fail without documents, but tests initialization)
    try:
        result = rag.query(
            question="Test question",
            return_source_documents=True
        )
        logger.info(f"Test result: {result}")
    except Exception as e:
        logger.error(f"Test failed (expected if no documents): {e}")
    
    logger.info("Quick test completed")


if __name__ == "__main__":
    quick_test()