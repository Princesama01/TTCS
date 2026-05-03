from typing import Literal, Optional

from pydantic import BaseModel, conint, confloat, constr


class SearchRequest(BaseModel):
    query: constr(min_length=1, max_length=5000)
    vector_name: constr(pattern=r"^(micro|macro|xref)$") = "micro"
    top_k: conint(ge=1, le=100) = 5
    version: Optional[constr(pattern=r"^v\d+$")] = None
    article_no: Optional[constr(pattern=r"^\d+$")] = None
    clause_no: Optional[constr(pattern=r"^\d+(\.\d+)*$")] = None
    doc_id: Optional[constr(min_length=1, max_length=120)] = None
    search_mode: Literal["vector", "hybrid"] = "hybrid"
    rerank_alpha: confloat(ge=0.0, le=1.0) = 0.75
    candidate_multiplier: conint(ge=1, le=20) = 5


class QuestionRequest(BaseModel):
    question: constr(min_length=1, max_length=5000)
    article_no: Optional[constr(pattern=r"^\d+$")] = None
    clause_no: Optional[constr(pattern=r"^\d+(\.\d+)*$")] = None
    version: Optional[constr(pattern=r"^v\d+$")] = None
    doc_id: Optional[constr(min_length=1, max_length=120)] = None
    top_k: conint(ge=1, le=20) = 5
    search_mode: Literal["vector", "hybrid"] = "hybrid"
    rerank_alpha: confloat(ge=0.0, le=1.0) = 0.75
    candidate_multiplier: conint(ge=1, le=20) = 5
    use_context: bool = True


class CompareDocumentsRequest(BaseModel):
    doc_id_1: str
    doc_id_2: str
    mode: Literal["hybrid", "semantic", "llm", "difflib_llm"] = "hybrid"
    semantic_threshold: confloat(ge=0.5, le=0.99) = 0.88
    candidate_threshold: confloat(ge=0.3, le=0.95) = 0.60
    llm_confidence_threshold: confloat(ge=0.0, le=1.0) = 0.70
    max_segments: conint(ge=1, le=300) = 120
    changed_only: bool = True
