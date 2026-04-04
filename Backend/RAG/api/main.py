"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from loguru import logger
import uvicorn

from api.routes import router, set_rag_pipeline
from src.rag_pipeline import RAGPipeline
from config import settings

# Configure logging
logger.add(
    Path(settings.LOGS_DIR) / "api.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Document Q&A System",
    description="Internal Document Q&A system using RAG with Llama 3",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["RAG API"])

# Serve static files (web UI)
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on startup"""
    logger.info("Starting RAG API server...")
    
    try:
        # Initialize RAG pipeline
        rag_pipeline = RAGPipeline(load_existing=True)
        set_rag_pipeline(rag_pipeline)
        
        logger.info("✓ RAG pipeline initialized successfully")
        logger.info(f"✓ API server started at http://{settings.API_HOST}:{settings.API_PORT}")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
        logger.warning("Server will start but may not function correctly")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main page"""
    web_file = Path(__file__).parent.parent / "web" / "index.html"
    
    if web_file.exists():
        return HTMLResponse(content=web_file.read_text(encoding='utf-8'))
    
    return HTMLResponse(
        content="""
        <html>
            <head>
                <title>RAG Document Q&A</title>
            </head>
            <body>
                <h1>RAG Document Q&A System</h1>
                <p>API is running. Visit <a href="/api/docs">/api/docs</a> for documentation.</p>
            </body>
        </html>
        """
    )


def main():
    """Run the API server"""
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
