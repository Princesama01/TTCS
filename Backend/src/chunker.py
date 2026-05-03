import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import settings
from src.structure_parser import StructureNode


@dataclass
class LegalChunk:
    text: str
    chunk_type: str
    doc_id: str
    version: str
    hash: str
    article_no: str
    clause_no: Optional[str] = None
    point_no: Optional[str] = None
    structure_path: str = ""
    char_start: int = 0
    char_end: int = 0
    page_number: int = 1
    chunk_id: str = ""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_text(text: str, max_chars: int, overlap: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    segments = []
    start = 0
    while start < len(text):
        end = start + max_chars
        segments.append(text[start:end])
        start = end - overlap if overlap > 0 else end
    return segments


class HierarchicalChunker:
    def __init__(self, cfg=None):
        cfg = cfg or settings
        self.micro_chars = cfg.MICRO_CHUNK_SIZE * 4
        self.micro_overlap = cfg.MICRO_CHUNK_OVERLAP * 4
        self.macro_chars = cfg.MACRO_CHUNK_SIZE * 4
        self.macro_overlap = cfg.MACRO_CHUNK_OVERLAP * 4
        self.xref_chars = cfg.XREF_CHUNK_SIZE * 4
        self.xref_overlap = cfg.XREF_CHUNK_OVERLAP * 4

    def chunk_document(self, nodes: List[StructureNode], doc_id: str, version: str) -> Dict[str, List[LegalChunk]]:
        return {
            "micro": self._chunk_micro(nodes, doc_id, version),
            "macro": self._chunk_macro(nodes, doc_id, version),
            "xref": self._chunk_xref(nodes, doc_id, version),
        }

    def _chunk_micro(self, nodes: List[StructureNode], doc_id: str, version: str) -> List[LegalChunk]:
        chunks = []
        for article in nodes:
            if article.children:
                for clause in article.children:
                    sources = clause.children if clause.children else [clause]
                    for node in sources:
                        chunks.extend(
                            self._make_chunks(
                                node.content,
                                "micro",
                                doc_id,
                                version,
                                node.article_no,
                                node.clause_no,
                                node.point_no,
                                node.structure_path,
                                node.char_start,
                                node.char_end,
                                self.micro_chars,
                                self.micro_overlap,
                            )
                        )
            else:
                chunks.extend(
                    self._make_chunks(
                        article.content,
                        "micro",
                        doc_id,
                        version,
                        article.article_no,
                        None,
                        None,
                        article.structure_path,
                        article.char_start,
                        article.char_end,
                        self.micro_chars,
                        self.micro_overlap,
                    )
                )
        return chunks

    def _chunk_macro(self, nodes: List[StructureNode], doc_id: str, version: str) -> List[LegalChunk]:
        chunks = []
        for article in nodes:
            chunks.extend(
                self._make_chunks(
                    article.content,
                    "macro",
                    doc_id,
                    version,
                    article.article_no,
                    None,
                    None,
                    article.structure_path,
                    article.char_start,
                    article.char_end,
                    self.macro_chars,
                    self.macro_overlap,
                )
            )
        return chunks

    def _chunk_xref(self, nodes: List[StructureNode], doc_id: str, version: str) -> List[LegalChunk]:
        full_text = "\n\n".join(n.content for n in nodes)
        return self._make_chunks(
            full_text,
            "xref",
            doc_id,
            version,
            article_no="all",
            clause_no=None,
            point_no=None,
            structure_path="full_document",
            char_start=0,
            char_end=len(full_text),
            max_chars=self.xref_chars,
            overlap=self.xref_overlap,
        )

    def _make_chunks(
        self,
        text: str,
        chunk_type: str,
        doc_id: str,
        version: str,
        article_no: str,
        clause_no,
        point_no,
        structure_path: str,
        char_start: int,
        char_end: int,
        max_chars: int,
        overlap: int,
    ) -> List[LegalChunk]:
        segments = _split_text(text, max_chars, overlap)
        result = []
        offset = char_start
        for seg in segments:
            page_num = (offset // 2000) + 1
            chunk_hash = _hash_text(seg)
            chunk_id = f"{doc_id}_{version}_{article_no}_{chunk_type}_{chunk_hash[:8]}"
            result.append(
                LegalChunk(
                    text=seg,
                    chunk_type=chunk_type,
                    doc_id=doc_id,
                    version=version,
                    hash=chunk_hash,
                    article_no=article_no or "",
                    clause_no=clause_no,
                    point_no=point_no,
                    structure_path=structure_path,
                    char_start=offset,
                    char_end=offset + len(seg),
                    page_number=page_num,
                    chunk_id=chunk_id,
                )
            )
            offset += len(seg) - overlap if overlap > 0 else len(seg)
        return result
