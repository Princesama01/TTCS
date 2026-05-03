import io
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.ollama_client import OllamaClient
from api.dependencies import shutdown_pipeline
from config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ = _app
    yield
    await shutdown_pipeline()


app = FastAPI(
    title="Legal Document Comparison API (Backend)",
    description="Refactored API only for features currently used by Frontend",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

from api.routers.compare import router as compare_router
from api.routers.documents import router as documents_router
from api.routers.evaluation import router as evaluation_router
from api.routers.rag import router as rag_router
from api.routers.stats import router as stats_router
from api.routers.upload import router as upload_router

app.include_router(documents_router)
app.include_router(upload_router)
app.include_router(rag_router)
app.include_router(compare_router)
app.include_router(stats_router)
app.include_router(evaluation_router)


@app.get("/")
async def root():
    return {
        "message": "Legal Document Comparison API (Backend)",
        "version": "3.0.0",
        "endpoints": {
            "documents": "/api/documents",
            "upload": "/api/upload",
            "search": "/api/search",
            "ask": "/api/ask",
            "compare_documents": "/api/compare-documents",
            "stats": "/api/stats",
            "evaluation": "/api/evaluation",
            "health": "/api/health",
        },
    }


@app.get("/api/health")
async def api_health():
    ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model_name=settings.OLLAMA_MODEL)
    ollama_status = ollama.health_check()
    return {
        "status": "healthy",
        "pipeline": "ready",
        "ollama": ollama_status.get("status", "unavailable"),
        "model": ollama_status.get("resolved_model", settings.OLLAMA_MODEL),
        "ollama_detail": ollama_status,
    }


@app.get("/health")
async def health():
    return await api_health()

