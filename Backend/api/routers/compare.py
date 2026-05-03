from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_pipeline
from api.models.requests import CompareDocumentsRequest
from api.ollama_client import OllamaClient
from api.pipeline import LegalVectorPipeline
from api.services.compare_pipeline_service import (
    run_difflib_llm_compare,
    run_llm_compare,
    run_semantic_compare,
)
from api.services.compare_service import CompareService
from api.services.document_service import DocumentService
from api.services.upload_service import UploadService
from config import settings

router = APIRouter(prefix="/api", tags=["compare"])
ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model_name=settings.OLLAMA_MODEL)


def get_document_service() -> DocumentService:
    return DocumentService()


def get_upload_service(pipeline: LegalVectorPipeline = Depends(get_pipeline)) -> UploadService:
    return UploadService(pipeline=pipeline)


@router.post("/compare-documents")
async def compare_two_documents(
    request: CompareDocumentsRequest,
    pipeline: LegalVectorPipeline = Depends(get_pipeline),
    upload_service: UploadService = Depends(get_upload_service),
    doc_service: DocumentService = Depends(get_document_service),
):
    if request.doc_id_1 == request.doc_id_2:
        raise HTTPException(status_code=400, detail="Cannot compare the same document")

    doc1_data = upload_service.get_document_content(request.doc_id_1)
    doc2_data = upload_service.get_document_content(request.doc_id_2)
    if not doc1_data or not doc2_data:
        raise HTTPException(status_code=404, detail="One or both documents not found or not processed yet")

    doc1_content = doc1_data.get("content", "")
    doc2_content = doc2_data.get("content", "")
    if not doc1_content or not doc2_content:
        raise HTTPException(status_code=400, detail="One or both documents have empty content")

    doc1_info = doc_service.get_document(request.doc_id_1)
    doc2_info = doc_service.get_document(request.doc_id_2)

    mode = request.mode

    if mode == "semantic":
        result = run_semantic_compare(
            embedder=pipeline.embedder,
            text_1=doc1_content,
            text_2=doc2_content,
            semantic_threshold=request.semantic_threshold,
            candidate_threshold=request.candidate_threshold,
            max_segments=request.max_segments,
        )
    elif mode == "difflib_llm":
        try:
            result = run_difflib_llm_compare(
                ollama=ollama,
                text_1=doc1_content,
                text_2=doc2_content,
                llm_confidence_threshold=request.llm_confidence_threshold,
                max_segments=request.max_segments,
            )
        except ValueError as e:
            raise HTTPException(status_code=502, detail=f"LLM judge parse error: {str(e)}")
    else:
        try:
            result = run_llm_compare(
                ollama=ollama,
                embedder=pipeline.embedder,
                text_1=doc1_content,
                text_2=doc2_content,
                llm_confidence_threshold=request.llm_confidence_threshold,
                semantic_threshold=request.semantic_threshold,
                candidate_threshold=request.candidate_threshold,
                max_segments=request.max_segments,
            )
        except ValueError as e:
            raise HTTPException(status_code=502, detail=f"LLM judge parse error: {str(e)}")

    segments = result.get("segments", [])
    segments_changed = result.get("segments_changed", [])
    display_segments = segments_changed if request.changed_only else segments

    changes = []
    change_details = {}
    for idx, seg in enumerate(display_segments, start=1):
        change_id = f"chg-{idx}"
        source_preview = (seg.get("source") or "")[:220]
        target_preview = (seg.get("target") or "")[:220]
        change_type = seg.get("verdict", "changed_meaning")
        changes.append(
            {
                "id": change_id,
                "type": change_type,
                "title": f"{change_type.upper()} #{idx}",
                "confidence": seg.get("confidence", 0.0),
                "method": seg.get("method", ""),
                "source_preview": source_preview,
                "target_preview": target_preview,
            }
        )
        change_details[change_id] = seg

    points1 = pipeline.get_document_chunks(request.doc_id_1, chunk_type="micro", limit=80)
    points2 = pipeline.get_document_chunks(request.doc_id_2, chunk_type="micro", limit=80)
    context1 = CompareService.build_vector_context(points1)
    context2 = CompareService.build_vector_context(points2)

    ai_summary = CompareService.generate_ai_summary(
        ollama=ollama,
        doc1_name=doc1_info.get("name", request.doc_id_1),
        doc2_name=doc2_info.get("name", request.doc_id_2),
        changes=display_segments,
        context1=context1 if mode in ["hybrid", "semantic"] else doc1_content[:2500],
        context2=context2 if mode in ["hybrid", "semantic"] else doc2_content[:2500],
        mode=mode,
    )

    return {
        "success": True,
        "mode": mode,
        "config": {
            "semantic_threshold": request.semantic_threshold,
            "candidate_threshold": request.candidate_threshold,
            "llm_confidence_threshold": request.llm_confidence_threshold,
            "max_segments": request.max_segments,
            "changed_only": request.changed_only,
        },
        "doc1_info": {
            "id": doc1_info.get("id"),
            "name": doc1_info.get("name"),
            "chunk_count": doc1_info.get("chunk_count", 0),
            "size": doc1_info.get("size", 0),
            "created_at": doc1_info.get("created_at", ""),
        },
        "doc2_info": {
            "id": doc2_info.get("id"),
            "name": doc2_info.get("name"),
            "chunk_count": doc2_info.get("chunk_count", 0),
            "size": doc2_info.get("size", 0),
            "created_at": doc2_info.get("created_at", ""),
        },
        "doc1_content": doc1_content,
        "doc2_content": doc2_content,
        "meaning_preserved": result.get("meaning_preserved"),
        "summary": result.get("summary", {}),
        "segments": segments,
        "segments_changed": segments_changed,
        "stage_outputs": result.get("stage_outputs", {}),
        "changes": changes,
        "change_details": change_details,
        "changes_count": len(changes),
        "ai_summary": ai_summary,
    }
