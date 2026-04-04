"""
Configuration management for RAG system
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Model Configuration
    LLAMA_MODEL_PATH: str = "models/llama-3-8b-instruct-q4_K_M.gguf"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Vector Database
    FAISS_INDEX_PATH: str = "data/vector_store/faiss_index"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 3
    SIMILARITY_THRESHOLD: float = 0.7
    
    # LLM Configuration
    N_GPU_LAYERS: int = 0  # -1 for full GPU offload
    N_CTX: int = 4096
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 512
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ENABLE_CORS: bool = True
    
    # Performance
    N_BATCH: int = 512
    N_THREADS: int = 4
    
    # Data Paths
    PDF_DATA_DIR: str = "data/documents"
    PROCESSED_DATA_DIR: str = "data/processed"
    LOGS_DIR: str = "logs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            Path(self.PDF_DATA_DIR),
            Path(self.PROCESSED_DATA_DIR),
            Path(self.LOGS_DIR),
            Path(self.FAISS_INDEX_PATH).parent,
            Path(self.LLAMA_MODEL_PATH).parent
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
