from fastapi import APIRouter, Depends

from api.dependencies import get_pipeline
from api.models.requests import QuestionRequest, SearchRequest
from api.ollama_client import OllamaClient
from api.pipeline import LegalVectorPipeline
from config import settings

router = APIRouter(prefix="/api", tags=["rag"])
ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model_name=settings.OLLAMA_MODEL)


@router.post("/search")
async def search_documents(request: SearchRequest, pipeline: LegalVectorPipeline = Depends(get_pipeline)):
    hits = pipeline.search(
        query=request.query,
        vector_name=request.vector_name,
        top_k=request.top_k,
        version=request.version,
        doc_id=request.doc_id,
        article_no=request.article_no,
        clause_no=request.clause_no,
        search_mode=request.search_mode,
        rerank_alpha=request.rerank_alpha,
        candidate_multiplier=request.candidate_multiplier,
    )
    results = []
    for hit in hits:
        p = hit.payload
        results.append(
            {
                "score": hit.score if hasattr(hit, "score") else 0,
                "content": p.get("content", ""),
                "version": p.get("version", ""),
                "article_no": p.get("article_no", ""),
                "structure_path": p.get("structure_path", ""),
                "page_number": p.get("page_number", 0),
                "chunk_type": p.get("chunk_type", ""),
            }
        )
    return {
        "success": True,
        "query": request.query,
        "results": results,
        "search_mode": request.search_mode,
        "applied_filters": {
            "version": request.version,
            "doc_id": request.doc_id,
            "article_no": request.article_no,
            "clause_no": request.clause_no,
        },
    }


@router.post("/ask")
async def ask_question(request: QuestionRequest, pipeline: LegalVectorPipeline = Depends(get_pipeline)):
    context = ""
    retrieval_citations = []
    llm_result = {
        "status": "insufficient_context",
        "answer": "Không có đủ dữ liệu để kết luận.",
        "citations": [],
        "confidence": "low",
        "confidence_reason": "Không có ngữ cảnh truy xuất.",
    }
    if request.use_context:
        hits = pipeline.search(
            query=request.question,
            vector_name="micro",
            top_k=request.top_k,
            version=request.version,
            doc_id=request.doc_id,
            article_no=request.article_no,
            clause_no=request.clause_no,
            search_mode=request.search_mode,
            rerank_alpha=request.rerank_alpha,
            candidate_multiplier=request.candidate_multiplier,
        )
        for hit in hits:
            p = hit.payload
            context += f"\n[{p.get('structure_path', '')}] {p.get('content', '')}\n"
            retrieval_citations.append(
                {
                    "content": p.get("content", ""),
                    "version": p.get("version", ""),
                    "article_no": p.get("article_no", ""),
                    "structure_path": p.get("structure_path", ""),
                    "page_number": p.get("page_number", 0),
                    "score": hit.score if hasattr(hit, "score") else 0,
                }
            )
        valid_paths = [c.get("structure_path", "") for c in retrieval_citations if c.get("structure_path")]
        llm_result = ollama.ask_question_with_citations(
            question=request.question,
            context=context,
            valid_paths=valid_paths,
        )

    return {
        "success": True,
        "question": request.question,
        "answer": llm_result.get("answer", "Không có đủ dữ liệu để kết luận."),
        "status": llm_result.get("status", "insufficient_context"),
        "confidence": llm_result.get("confidence", "low"),
        "confidence_reason": llm_result.get("confidence_reason", ""),
        "citations": retrieval_citations,
        "llm_citations": llm_result.get("citations", []),
        "retrieval_count": len(retrieval_citations),
        "search_mode": request.search_mode if request.use_context else "none",
    }
