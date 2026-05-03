from typing import Dict, Optional

from config import settings
from src.chunker import HierarchicalChunker
from src.chunking_strategies import HybridChunker, RecursiveChunker, StructuralChunker
from src.diff_engine import LegalDiffEngine
from src.embedder import LegalEmbedder
from src.retriever import LegalRetriever
from src.structure_parser import LegalStructureParser
from src.vector_store import LegalVectorStore


class LegalVectorPipeline:
    def __init__(self, storage_path: Optional[str] = None):
        self.parser = LegalStructureParser()
        self.chunker = HierarchicalChunker(settings)
        self.embedder = LegalEmbedder(settings.EMBEDDING_MODEL)
        self.store = LegalVectorStore(
            path=storage_path,
            collection_name=settings.COLLECTION_NAME,
            dim=settings.EMBEDDING_DIM,
        )
        self.retriever = LegalRetriever(self.store, self.embedder)
        self.diff_engine = LegalDiffEngine()
        self.store.create_collection()

    def index_document(self, text: str, doc_id: str, version: str = "v1") -> dict:
        nodes = self.parser.parse(text)
        chunk_sets = self.chunker.chunk_document(nodes, doc_id, version)
        strategy = getattr(settings, "CHUNKING_STRATEGY", "hierarchical").strip().lower()
        if strategy in {"structural", "recursive", "hybrid"}:
            max_chars = self.chunker.micro_chars
            overlap_chars = self.chunker.micro_overlap
            if strategy == "structural":
                strategy_chunker = StructuralChunker(max_chars=max_chars, overlap_chars=overlap_chars)
            elif strategy == "hybrid":
                strategy_chunker = HybridChunker(max_chars=max_chars, overlap_chars=overlap_chars)
            else:
                strategy_chunker = RecursiveChunker(max_chars=max_chars, overlap_chars=overlap_chars)
            chunk_sets["micro"] = strategy_chunker.chunk_text(text=text, doc_id=doc_id, version=version)

        stats = {}
        total = 0
        for chunk_type, chunks in chunk_sets.items():
            if not chunks:
                stats[chunk_type] = 0
                continue
            texts = [c.text for c in chunks]
            vectors = self.embedder.embed(texts)
            points = []
            for chunk, vec in zip(chunks, vectors):
                payload = {
                    "content": chunk.text,
                    "chunk_type": chunk_type,
                    "doc_id": chunk.doc_id,
                    "version": chunk.version,
                    "hash": chunk.hash,
                    "article_no": chunk.article_no,
                    "clause_no": chunk.clause_no or "",
                    "point_no": chunk.point_no or "",
                    "structure_path": chunk.structure_path,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "page_number": chunk.page_number,
                    "chunk_id": chunk.chunk_id,
                }
                points.append(self.store.build_point(chunk_type, vec.tolist(), payload))
            self.store.upsert_points(points)
            stats[chunk_type] = len(points)
            total += len(points)
        stats["total"] = total
        return stats

    def search(
        self,
        query: str,
        vector_name: str = "micro",
        top_k: int = 5,
        version: Optional[str] = None,
        doc_id: Optional[str] = None,
        article_no: Optional[str] = None,
        clause_no: Optional[str] = None,
        search_mode: str = "hybrid",
        rerank_alpha: float = 0.75,
        candidate_multiplier: int = 5,
    ) -> list:
        return self.retriever.search_all(
            query=query,
            vector_name=vector_name,
            top_k=top_k,
            version=version,
            doc_id=doc_id,
            article_no=article_no,
            clause_no=clause_no,
            search_mode=search_mode,
            rerank_alpha=rerank_alpha,
            candidate_multiplier=candidate_multiplier,
        )

    def get_document_chunks(self, doc_id: str, chunk_type: str = "micro", limit: int = 200):
        return self.store.scroll_by_doc(doc_id=doc_id, chunk_type=chunk_type, limit=limit)

    def compare_article(
        self,
        doc_id: str,
        article_no: str,
        vector_name: str = "micro",
        limit: int = 500,
    ) -> Dict:
        v1_chunks = self.store.scroll_filtered(
            version_filter="v1",
            article_filter=article_no,
            chunk_type=vector_name,
            doc_id_filter=doc_id,
            limit=limit,
        )
        v2_chunks = self.store.scroll_filtered(
            version_filter="v2",
            article_filter=article_no,
            chunk_type=vector_name,
            doc_id_filter=doc_id,
            limit=limit,
        )
        changes = self.diff_engine.compare_article(v1_chunks, v2_chunks, article_no)
        return {
            "doc_id": doc_id,
            "article_no": article_no,
            "vector_name": vector_name,
            "v1_chunks": len(v1_chunks),
            "v2_chunks": len(v2_chunks),
            "changes": changes,
            "report": self.diff_engine.generate_report(changes),
        }
