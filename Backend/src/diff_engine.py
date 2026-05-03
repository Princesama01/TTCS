import difflib
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MatchPair:
    chunk_v1: Optional[dict]
    chunk_v2: Optional[dict]
    match_type: str  # rule-based | semantic | none
    similarity_score: float = 0.0
    article_no: str = ""
    structure_path: str = ""


@dataclass
class ChangeRecord:
    article_no: str
    change_type: str
    v1_text: str
    v2_text: str
    diff_lines: List[str]
    similarity: float
    citation_v1: Optional[dict] = None
    citation_v2: Optional[dict] = None
    granularity: str = "chunk"


class LegalDiffEngine:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def create_match_pairs(self, v1_chunks: list, v2_chunks: list) -> List[MatchPair]:
        pairs: List[MatchPair] = []
        matched_v1 = set()
        matched_v2 = set()

        v1_by_path = {p.payload.get("structure_path", ""): (i, p) for i, p in enumerate(v1_chunks)}
        v2_by_path = {p.payload.get("structure_path", ""): (i, p) for i, p in enumerate(v2_chunks)}

        for path, (idx1, chunk1) in v1_by_path.items():
            if path and path in v2_by_path:
                idx2, chunk2 = v2_by_path[path]
                pairs.append(
                    MatchPair(
                        chunk_v1=chunk1.payload,
                        chunk_v2=chunk2.payload,
                        match_type="rule-based",
                        similarity_score=1.0,
                        article_no=chunk1.payload.get("article_no", ""),
                        structure_path=path,
                    )
                )
                matched_v1.add(idx1)
                matched_v2.add(idx2)

        unmatched_v1 = [(i, p) for i, p in enumerate(v1_chunks) if i not in matched_v1]
        unmatched_v2 = [(i, p) for i, p in enumerate(v2_chunks) if i not in matched_v2]

        for idx1, chunk1 in unmatched_v1:
            best_match = None
            best_score = 0.0
            best_idx = None
            for idx2, chunk2 in unmatched_v2:
                text1 = chunk1.payload.get("content", "")
                text2 = chunk2.payload.get("content", "")
                score = difflib.SequenceMatcher(None, text1, text2).ratio()
                if score > best_score and score > 0.7:
                    best_score = score
                    best_match = chunk2
                    best_idx = idx2
            if best_match is not None and best_idx is not None:
                pairs.append(
                    MatchPair(
                        chunk_v1=chunk1.payload,
                        chunk_v2=best_match.payload,
                        match_type="semantic",
                        similarity_score=best_score,
                        article_no=chunk1.payload.get("article_no", ""),
                        structure_path=chunk1.payload.get("structure_path", ""),
                    )
                )
                matched_v1.add(idx1)
                matched_v2.add(best_idx)

        for idx, chunk in enumerate(v1_chunks):
            if idx not in matched_v1:
                pairs.append(
                    MatchPair(
                        chunk_v1=chunk.payload,
                        chunk_v2=None,
                        match_type="none",
                        article_no=chunk.payload.get("article_no", ""),
                        structure_path=chunk.payload.get("structure_path", ""),
                    )
                )

        for idx, chunk in enumerate(v2_chunks):
            if idx not in matched_v2:
                pairs.append(
                    MatchPair(
                        chunk_v1=None,
                        chunk_v2=chunk.payload,
                        match_type="none",
                        article_no=chunk.payload.get("article_no", ""),
                        structure_path=chunk.payload.get("structure_path", ""),
                    )
                )

        return pairs

    def compare_article(self, v1_chunks: list, v2_chunks: list, article_no: str) -> List[ChangeRecord]:
        v1_texts = [p.payload.get("content", "") for p in v1_chunks]
        v2_texts = [p.payload.get("content", "") for p in v2_chunks]

        if not v1_texts and not v2_texts:
            return []
        if not v1_texts:
            return [
                self._create_change_record(article_no, "added", "", t, [], 0.0, None, p.payload)
                for t, p in zip(v2_texts, v2_chunks)
            ]
        if not v2_texts:
            return [
                self._create_change_record(article_no, "removed", t, "", [], 0.0, p.payload, None)
                for t, p in zip(v1_texts, v1_chunks)
            ]

        pairs = self.create_match_pairs(v1_chunks, v2_chunks)
        changes: List[ChangeRecord] = []

        for pair in pairs:
            if pair.chunk_v1 and pair.chunk_v2:
                if pair.chunk_v1.get("hash") != pair.chunk_v2.get("hash"):
                    v1_text = pair.chunk_v1.get("content", "")
                    v2_text = pair.chunk_v2.get("content", "")
                    diff = list(
                        difflib.unified_diff(
                            v1_text.splitlines(),
                            v2_text.splitlines(),
                            fromfile="v1",
                            tofile="v2",
                            lineterm="",
                        )
                    )
                    ratio = difflib.SequenceMatcher(None, v1_text, v2_text).ratio()
                    changes.append(
                        self._create_change_record(
                            article_no, "modified", v1_text, v2_text, diff, ratio, pair.chunk_v1, pair.chunk_v2
                        )
                    )
            elif pair.chunk_v2 and not pair.chunk_v1:
                changes.append(
                    self._create_change_record(
                        article_no, "added", "", pair.chunk_v2.get("content", ""), [], 0.0, None, pair.chunk_v2
                    )
                )
            elif pair.chunk_v1 and not pair.chunk_v2:
                changes.append(
                    self._create_change_record(
                        article_no, "removed", pair.chunk_v1.get("content", ""), "", [], 0.0, pair.chunk_v1, None
                    )
                )

        return changes

    @staticmethod
    def _create_change_record(
        article_no: str,
        change_type: str,
        v1_text: str,
        v2_text: str,
        diff_lines: List[str],
        similarity: float,
        citation_v1: Optional[dict] = None,
        citation_v2: Optional[dict] = None,
    ) -> ChangeRecord:
        return ChangeRecord(
            article_no=article_no,
            change_type=change_type,
            v1_text=v1_text,
            v2_text=v2_text,
            diff_lines=diff_lines,
            similarity=similarity,
            citation_v1=citation_v1,
            citation_v2=citation_v2,
        )

    def generate_report(self, all_changes: List[ChangeRecord]) -> str:
        if not all_changes:
            return "Khong phat hien thay doi."
        lines = [f"Phat hien {len(all_changes)} thay doi:\n"]
        for idx, c in enumerate(all_changes, 1):
            lines.append(f"  [{idx}] Dieu {c.article_no} - {c.change_type.upper()}")
            if c.change_type == "modified":
                lines.append(f"      Similarity: {c.similarity:.1%}")
            elif c.change_type == "added":
                lines.append(f"      + {c.v2_text[:120]}...")
            elif c.change_type == "removed":
                lines.append(f"      - {c.v1_text[:120]}...")
            lines.append("")
        return "\n".join(lines)
