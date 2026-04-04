"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    question: str = Field(..., description="User question", min_length=1)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    language: str = Field("vi", description="Response language (vi/en)")
    return_sources: bool = Field(False, description="Include source documents")


class SourceDocument(BaseModel):
    """Source document metadata"""
    content: str
    filename: str
    page: Optional[str]
    score: Optional[float]


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    answer: str
    conversation_id: Optional[str]
    retrieval_time: float
    generation_time: float
    total_time: float
    source_documents: Optional[List[SourceDocument]] = None


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    success: bool
    message: str
    processed_files: int
    total_chunks: int


class SourcesResponse(BaseModel):
    """Response for sources endpoint"""
    sources: List[Dict]
    query: str


class StatisticsResponse(BaseModel):
    """System statistics response"""
    vector_store: Dict
    llm: Dict
    active_conversations: int
    total_conversation_turns: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    components: Dict
