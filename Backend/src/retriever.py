import re
from typing import Optional

_ARTICLE_RE = re.compile(r"(?:Điều|điều|dieu)\s+(\d+)", re.IGNORECASE | re.UNICODE)
_CLAUSE_RE = re.compile(r"(?:Khoản|khoản|khoan)\s+(\d+)", re.IGNORECASE | re.UNICODE)
_TOKEN_RE = re.compile(r"[^\s\W]+", re.UNICODE)


def _parse_structural_query(query: str) -> tuple:
    article_no = None
    clause_no = None
    art_match = _ARTICLE_RE.search(query)
    if art_match:
        article_no = art_match.group(1)
    clause_match = _CLAUSE_RE.search(query)
    if clause_match and article_no:
        clause_no = f"{article_no}.{clause_match.group(1)}"
    semantic = _ARTICLE_RE.sub("", query)
    semantic = _CLAUSE_RE.sub("", semantic).strip()
    return article_no, clause_no, semantic


class LegalRetriever:
    def __init__(self, vector_store, embedder):
        self.store = vector_store
        self.embedder = embedder

    def search_all(
        self,
        query: str,
        vector_name: str = "micro",
        top_k: int = 10,
        version: Optional[str] = None,
        doc_id: Optional[str] = None,
        article_no: Optional[str] = None,
        clause_no: Optional[str] = None,
        search_mode: str = "hybrid",
        rerank_alpha: float = 0.75,
        candidate_multiplier: int = 5,
    ) -> list:
        inferred_article_no, inferred_clause_no, semantic = _parse_structural_query(query)
        article_filter = article_no or inferred_article_no
        clause_filter = clause_no or inferred_clause_no
        clause_filter = clause_filter if vector_name == "micro" else None

        mode = (search_mode or "vector").strip().lower()
        if mode not in {"vector", "hybrid"}:
            mode = "vector"

        candidate_multiplier = max(1, min(candidate_multiplier, 20))
        vector_limit = top_k if mode == "vector" else min(200, max(top_k, top_k * candidate_multiplier))
        qv = self.embedder.embed_single(semantic or query).tolist()
        vector_hits = self.store.search(
            vector_name=vector_name,
            query_vector=qv,
            limit=vector_limit,
            version_filter=version,
            article_filter=article_filter,
            clause_filter=clause_filter,
            doc_id_filter=doc_id,
        )
        if mode == "vector":
            return vector_hits[:top_k]

        alpha = min(1.0, max(0.0, rerank_alpha))
        hybrid_scored = []
        for hit in vector_hits:
            payload = hit.payload if hasattr(hit, "payload") else {}
            vector_score = float(hit.score) if hasattr(hit, "score") else 0.0
            keyword_score = self._keyword_score(semantic or query, payload)
            combined = (alpha * vector_score) + ((1.0 - alpha) * keyword_score)
            hybrid_scored.append((combined, vector_score, keyword_score, hit))

        hybrid_scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return [item[3] for item in hybrid_scored[:top_k]]

    @staticmethod
    def _keyword_score(query: str, payload: dict) -> float:
        query_tokens = set(_TOKEN_RE.findall((query or "").lower()))
        if not query_tokens:
            return 0.0

        content = payload.get("content", "")
        structure_path = payload.get("structure_path", "")
        article_no = payload.get("article_no", "")
        clause_no = payload.get("clause_no", "")
        haystack = f"{content}\n{structure_path}\n{article_no}\n{clause_no}".lower()
        content_tokens = set(_TOKEN_RE.findall(haystack))
        if not content_tokens:
            return 0.0

        overlap = len(query_tokens & content_tokens) / len(query_tokens)
        path_boost = 0.0
        if article_no and article_no in query:
            path_boost += 0.10
        if clause_no and clause_no in query:
            path_boost += 0.10
        return min(1.0, overlap + path_boost)
