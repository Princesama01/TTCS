"""
FastAPI routes for RAG system
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import shutil
from pathlib import Path
from loguru import logger
import uuid

from api.models import (
    ChatRequest,
    ChatResponse,
    SourceDocument,
    DocumentUploadResponse,
    SourcesResponse,
    StatisticsResponse,
    HealthResponse
)
from src.rag_pipeline import RAGPipeline
from config import settings

# Initialize router
router = APIRouter()

# Global RAG pipeline instance (will be set in main.py)
rag_pipeline: RAGPipeline = None


def set_rag_pipeline(pipeline: RAGPipeline):
    """Set the global RAG pipeline instance"""
    global rag_pipeline
    rag_pipeline = pipeline


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for Q&A
    
    Args:
        request: ChatRequest with question and options
        
    Returns:
        ChatResponse with answer and metadata
    """
    try:
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Query RAG system
        result = rag_pipeline.query(
            question=request.question,
            conversation_id=conversation_id,
            return_source_documents=request.return_sources,
            language=request.language
        )
        
        # Build response
        response = ChatResponse(
            answer=result["answer"],
            conversation_id=conversation_id,
            retrieval_time=result["retrieval_time"],
            generation_time=result["generation_time"],
            total_time=result["total_time"]
        )
        
        # Add source documents if requested
        if request.return_sources and "source_documents" in result:
            response.source_documents = [
                SourceDocument(
                    content=doc["content"][:500],  # Truncate for API response
                    filename=doc["metadata"].get("filename", "Unknown"),
                    page=str(doc["metadata"].get("page", "N/A")),
                    score=doc.get("score")
                )
                for doc in result["source_documents"]
            ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50)
):
    """
    Upload and process PDF documents
    
    Args:
        files: List of PDF files to upload
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        DocumentUploadResponse with processing results
    """
    try:
        # Create temporary directory for uploads
        upload_dir = Path(settings.PDF_DATA_DIR) / "uploads" / str(uuid.uuid4())
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded files
        saved_files = []
        for file in files:
            if not file.filename.endswith('.pdf'):
                continue
            
            file_path = upload_dir / file.filename
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file.file, f)
            saved_files.append(file_path)
        
        if not saved_files:
            raise HTTPException(
                status_code=400,
                detail="No valid PDF files provided"
            )
        
        # Process documents
        rag_pipeline.ingest_documents(
            pdf_directory=upload_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Get statistics
        stats = rag_pipeline.get_statistics()
        
        return DocumentUploadResponse(
            success=True,
            message=f"Successfully processed {len(saved_files)} documents",
            processed_files=len(saved_files),
            total_chunks=stats["vector_store"].get("total_vectors", 0)
        )
        
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/sources", response_model=SourcesResponse)
async def get_sources(question: str):
    """
    Get source documents for a question without generating answer
    
    Args:
        question: Query to find sources for
        
    Returns:
        SourcesResponse with source metadata
    """
    try:
        sources = rag_pipeline.get_sources(question)
        
        return SourcesResponse(
            sources=sources,
            query=question
        )
        
    except Exception as e:
        logger.error(f"Error getting sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """
    Clear conversation history
    
    Args:
        conversation_id: ID of conversation to clear
        
    Returns:
        Success message
    """
    try:
        rag_pipeline.clear_conversation(conversation_id)
        return {"message": f"Conversation {conversation_id} cleared"}
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    Get system statistics
    
    Returns:
        StatisticsResponse with system info
    """
    try:
        stats = rag_pipeline.get_statistics()
        return StatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns:
        HealthResponse with system status
    """
    try:
        stats = rag_pipeline.get_statistics()
        
        components = {
            "vector_store": "healthy" if stats["vector_store"].get("total_vectors", 0) > 0 else "empty",
            "llm": "healthy",
            "retriever": "healthy"
        }
        
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            components=components
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            components={"error": str(e)}
        )
