from datetime import datetime

from fastapi import APIRouter, Depends

from api.services.document_service import DocumentService

router = APIRouter(prefix="/api", tags=["statistics"])


def get_document_service() -> DocumentService:
    return DocumentService()


@router.get("/stats")
async def get_statistics(doc_service: DocumentService = Depends(get_document_service)):
    docs = doc_service.get_all_documents()
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)
    return {
        "success": True,
        "documents": len(docs),
        "chunks": total_chunks,
        "status": "online",
        "last_updated": datetime.now().isoformat(),
    }
