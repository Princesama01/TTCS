"""
Chunking Strategies for Legal Document RAG Optimization.

Three strategies to compare:
1. StructuralChunker  — chunk by legal structure boundaries (Điều/Khoản/Điểm)
2. RecursiveChunker   — recursive splitting by separator hierarchy
3. HybridChunker      — structural parse first, then recursive split for oversized nodes
"""

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional

from src.chunker import LegalChunk
from src.structure_parser import LegalStructureParser, StructureNode


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _make_chunk(
    text: str,
    chunk_type: str,
    doc_id: str,
    version: str,
    article_no: str,
    clause_no: Optional[str],
    point_no: Optional[str],
    structure_path: str,
    char_start: int,
    char_end: int,
) -> LegalChunk:
    chunk_hash = _hash_text(text)
    chunk_id = f"{doc_id}_{version}_{article_no}_{chunk_type}_{chunk_hash[:8]}"
    page_num = (char_start // 2000) + 1
    return LegalChunk(
        text=text,
        chunk_type=chunk_type,
        doc_id=doc_id,
        version=version,
        hash=chunk_hash,
        article_no=article_no or "",
        clause_no=clause_no,
        point_no=point_no,
        structure_path=structure_path,
        char_start=char_start,
        char_end=char_end,
        page_number=page_num,
        chunk_id=chunk_id,
    )


# ---------------------------------------------------------------------------
# Strategy 1: Structural Chunker
# ---------------------------------------------------------------------------

class StructuralChunker:
    """Chunk by legal structure boundaries. Each node (article/clause/point)
    becomes one chunk regardless of size. Preserves legal context perfectly
    but may produce very large or very small chunks."""

    def __init__(self, max_chars: int = 2048, overlap_chars: int = 0):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.parser = LegalStructureParser()

    def chunk_text(self, text: str, doc_id: str, version: str = "v1") -> List[LegalChunk]:
        nodes = self.parser.parse(text)
        if not nodes:
            # Fallback: treat entire text as one chunk
            return [_make_chunk(text, "structural", doc_id, version, "0", None, None, "full", 0, len(text))]
        chunks: List[LegalChunk] = []
        for article in nodes:
            if article.children:
                for clause in article.children:
                    if clause.children:
                        for point in clause.children:
                            chunks.append(
                                _make_chunk(
                                    point.content, "structural", doc_id, version,
                                    point.article_no, point.clause_no, point.point_no,
                                    point.structure_path, point.char_start, point.char_end,
                                )
                            )
                    else:
                        chunks.append(
                            _make_chunk(
                                clause.content, "structural", doc_id, version,
                                clause.article_no, clause.clause_no, None,
                                clause.structure_path, clause.char_start, clause.char_end,
                            )
                        )
            else:
                chunks.append(
                    _make_chunk(
                        article.content, "structural", doc_id, version,
                        article.article_no, None, None,
                        article.structure_path, article.char_start, article.char_end,
                    )
                )
        return chunks


# ---------------------------------------------------------------------------
# Strategy 2: Recursive Chunker
# ---------------------------------------------------------------------------

_SEPARATORS = ["\n\n", "\n", ". ", ", ", " "]


class RecursiveChunker:
    """Recursive text splitting by separator hierarchy.
    Tries the largest separator first; if a segment is still too big,
    recurses with the next separator."""

    def __init__(self, max_chars: int = 2048, overlap_chars: int = 0):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk_text(self, text: str, doc_id: str, version: str = "v1") -> List[LegalChunk]:
        raw_segments = self._recursive_split(text, separators=list(_SEPARATORS))
        chunks: List[LegalChunk] = []
        offset = 0
        for seg in raw_segments:
            # Find actual position in original text
            idx = text.find(seg, offset)
            if idx == -1:
                idx = offset
            chunks.append(
                _make_chunk(
                    seg, "recursive", doc_id, version,
                    "", None, None, "recursive", idx, idx + len(seg),
                )
            )
            offset = idx + len(seg) - self.overlap_chars
            if offset < 0:
                offset = 0
        # Try to assign article_no from content
        article_re = re.compile(r"(?:Điều|Dieu)\s+(\d+)", re.UNICODE)
        for chunk in chunks:
            m = article_re.search(chunk.text)
            if m:
                chunk.article_no = m.group(1)
        return chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.max_chars:
            return [text] if text.strip() else []

        if not separators:
            # Hard split as last resort
            return self._hard_split(text)

        sep = separators[0]
        remaining_seps = separators[1:]
        parts = text.split(sep)

        segments: List[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                if current:
                    segments.append(current)
                if len(part) > self.max_chars:
                    # Recurse with smaller separator
                    segments.extend(self._recursive_split(part, remaining_seps))
                    current = ""
                else:
                    current = part

        if current.strip():
            segments.append(current)

        # Apply overlap
        if self.overlap_chars > 0 and len(segments) > 1:
            segments = self._apply_overlap(segments)

        return segments

    def _hard_split(self, text: str) -> List[str]:
        segments = []
        start = 0
        while start < len(text):
            end = start + self.max_chars
            segments.append(text[start:end])
            start = end - self.overlap_chars if self.overlap_chars > 0 else end
        return segments

    def _apply_overlap(self, segments: List[str]) -> List[str]:
        if self.overlap_chars <= 0:
            return segments
        result = [segments[0]]
        for i in range(1, len(segments)):
            prev = segments[i - 1]
            overlap_text = prev[-self.overlap_chars:] if len(prev) >= self.overlap_chars else prev
            result.append(overlap_text + segments[i])
        return result


# ---------------------------------------------------------------------------
# Strategy 3: Hybrid Chunker
# ---------------------------------------------------------------------------

class HybridChunker:
    """Structural parse first, then recursive split for oversized nodes.
    Best of both worlds: preserves legal metadata while controlling chunk size."""

    def __init__(self, max_chars: int = 2048, overlap_chars: int = 0):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.parser = LegalStructureParser()
        self.recursive = RecursiveChunker(max_chars=max_chars, overlap_chars=overlap_chars)

    def chunk_text(self, text: str, doc_id: str, version: str = "v1") -> List[LegalChunk]:
        nodes = self.parser.parse(text)
        if not nodes:
            return self.recursive.chunk_text(text, doc_id, version)

        chunks: List[LegalChunk] = []
        for article in nodes:
            self._process_node(article, doc_id, version, chunks)
        return chunks

    def _process_node(self, node: StructureNode, doc_id: str, version: str, chunks: List[LegalChunk]):
        """Process a single structure node. If it has children, recurse.
        If a leaf node is too big, apply recursive splitting with metadata preserved."""
        if node.children:
            for child in node.children:
                self._process_node(child, doc_id, version, chunks)
        else:
            # Leaf node — check if it fits in max_chars
            if len(node.content) <= self.max_chars:
                chunks.append(
                    _make_chunk(
                        node.content, "hybrid", doc_id, version,
                        node.article_no, node.clause_no, node.point_no,
                        node.structure_path, node.char_start, node.char_end,
                    )
                )
            else:
                # Too big — apply recursive splitting but keep metadata
                sub_segments = self.recursive._recursive_split(node.content, list(_SEPARATORS))
                offset = node.char_start
                for seg in sub_segments:
                    idx = node.content.find(seg, offset - node.char_start)
                    if idx == -1:
                        idx = 0
                    abs_start = node.char_start + idx
                    chunks.append(
                        _make_chunk(
                            seg, "hybrid", doc_id, version,
                            node.article_no, node.clause_no, node.point_no,
                            node.structure_path, abs_start, abs_start + len(seg),
                        )
                    )
                    offset = abs_start + len(seg)
