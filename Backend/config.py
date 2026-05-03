import os
from pathlib import Path


class Settings:
    PROJECT_ROOT = Path(__file__).parent.resolve()
    DATA_DIR = PROJECT_ROOT / "data"
    QDRANT_PATH = str(DATA_DIR / "qdrant_storage")

    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384
    COLLECTION_NAME = "legal_contracts"

    # Chunking configuration (optimized via chunking experiment)
    # Best grid result on current dataset: recursive_s256_o0
    CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "recursive")
    MICRO_CHUNK_SIZE = 256
    MICRO_CHUNK_OVERLAP = 0
    MACRO_CHUNK_SIZE = 512
    MACRO_CHUNK_OVERLAP = 0
    XREF_CHUNK_SIZE = 1024
    XREF_CHUNK_OVERLAP = 0

    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://localhost:8010",
        "http://localhost:5000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8010",
        "http://127.0.0.1:5000",
    ]
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-3B")


settings = Settings()
