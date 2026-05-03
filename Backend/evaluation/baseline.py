import difflib
import re
from dataclasses import dataclass
from math import log
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class BaselineChange:
    article_no: str
    change_type: str
    v1_text: str
    v2_text: str
    similarity: float


@dataclass
class BaselineSearchResult:
    article_no: str
    content: str
    score: float
    version: str


@dataclass
class TextComparisonResult:
    removed: List[str]
    added: List[str]
    changed: List[Dict[str, str]]


class BaselineSystem:
    ARTICLE_RE = re.compile(r"(?:Điều|điều|Dieu|dieu)\s+(\d+)\.\s*(.+?)(?:\n|$)", re.UNICODE)

    def __init__(self):
        self.documents: Dict[str, Dict[str, str]] = {}
        self.articles: Dict[str, Dict[str, Dict[str, str]]] = {}

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())

    @classmethod
    def _extract_units(cls, text: str) -> List[str]:
        units: List[str] = []
        for line in text.splitlines():
            candidate = cls._normalize_text(line)
            if candidate:
                units.append(candidate)
        return units

    @staticmethod
    def _best_pairing(removed: List[str], added: List[str], threshold: float) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
        matched_removed = set()
        matched_added = set()
        changed: List[Dict[str, str]] = []

        for i, left in enumerate(removed):
            best_j = -1
            best_score = 0.0
            for j, right in enumerate(added):
                if j in matched_added:
                    continue
                score = difflib.SequenceMatcher(None, left, right).ratio()
                if score > best_score:
                    best_score = score
                    best_j = j
            if best_j >= 0 and best_score >= threshold:
                matched_removed.add(i)
                matched_added.add(best_j)
                changed.append(
                    {
                        "before": left,
                        "after": added[best_j],
                        "similarity": round(best_score, 4),
                    }
                )

        remaining_removed = [text for idx, text in enumerate(removed) if idx not in matched_removed]
        remaining_added = [text for idx, text in enumerate(added) if idx not in matched_added]
        return changed, remaining_removed, remaining_added

    @staticmethod
    def _keyword_similarity(left: str, right: str) -> float:
        left_terms = {w for w in re.findall(r"[^\W_]+", left.lower(), re.UNICODE) if len(w) > 2}
        right_terms = {w for w in re.findall(r"[^\W_]+", right.lower(), re.UNICODE) if len(w) > 2}
        if not left_terms or not right_terms:
            return 0.0
        overlap = len(left_terms & right_terms)
        union = len(left_terms | right_terms)
        return overlap / union if union else 0.0

    @staticmethod
    def _tfidf_vector(text: str, idf: Dict[str, float]) -> Dict[str, float]:
        terms = [w for w in re.findall(r"[^\W_]+", text.lower(), re.UNICODE) if len(w) > 1]
        if not terms:
            return {}
        tf: Dict[str, float] = {}
        total = len(terms)
        for term in terms:
            tf[term] = tf.get(term, 0.0) + 1.0 / total
        vec: Dict[str, float] = {}
        for term, tf_value in tf.items():
            vec[term] = tf_value * idf.get(term, 0.0)
        return vec

    @staticmethod
    def _cosine_sparse(left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(v * right.get(k, 0.0) for k, v in left.items())
        if dot == 0.0:
            return 0.0
        left_norm = sum(v * v for v in left.values()) ** 0.5
        right_norm = sum(v * v for v in right.values()) ** 0.5
        denom = left_norm * right_norm
        return dot / denom if denom else 0.0

    def _best_pairing_keyword(self, removed: List[str], added: List[str], threshold: float) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
        matched_removed = set()
        matched_added = set()
        changed: List[Dict[str, str]] = []

        for i, left in enumerate(removed):
            best_j = -1
            best_score = 0.0
            for j, right in enumerate(added):
                if j in matched_added:
                    continue
                score = self._keyword_similarity(left, right)
                if score > best_score:
                    best_score = score
                    best_j = j
            if best_j >= 0 and best_score >= threshold:
                matched_removed.add(i)
                matched_added.add(best_j)
                changed.append({"before": left, "after": added[best_j], "similarity": round(best_score, 4)})

        remaining_removed = [text for idx, text in enumerate(removed) if idx not in matched_removed]
        remaining_added = [text for idx, text in enumerate(added) if idx not in matched_added]
        return changed, remaining_removed, remaining_added

    def _best_pairing_tfidf(self, removed: List[str], added: List[str], threshold: float) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
        docs = removed + added
        doc_count = len(docs)
        if doc_count == 0:
            return [], removed, added
        df: Dict[str, int] = {}
        for doc in docs:
            seen: Set[str] = set()
            for term in re.findall(r"[^\W_]+", doc.lower(), re.UNICODE):
                if len(term) <= 1 or term in seen:
                    continue
                seen.add(term)
                df[term] = df.get(term, 0) + 1

        idf = {term: log((1 + doc_count) / (1 + freq)) + 1.0 for term, freq in df.items()}
        removed_vecs = [self._tfidf_vector(text, idf) for text in removed]
        added_vecs = [self._tfidf_vector(text, idf) for text in added]

        matched_removed = set()
        matched_added = set()
        changed: List[Dict[str, str]] = []
        for i, left_vec in enumerate(removed_vecs):
            best_j = -1
            best_score = 0.0
            for j, right_vec in enumerate(added_vecs):
                if j in matched_added:
                    continue
                score = self._cosine_sparse(left_vec, right_vec)
                if score > best_score:
                    best_score = score
                    best_j = j
            if best_j >= 0 and best_score >= threshold:
                matched_removed.add(i)
                matched_added.add(best_j)
                changed.append({"before": removed[i], "after": added[best_j], "similarity": round(best_score, 4)})

        remaining_removed = [text for idx, text in enumerate(removed) if idx not in matched_removed]
        remaining_added = [text for idx, text in enumerate(added) if idx not in matched_added]
        return changed, remaining_removed, remaining_added

    def compare_texts(
        self,
        before_text: str,
        after_text: str,
        method: str = "rule_based_diff",
        changed_threshold: float = 0.8,
    ) -> TextComparisonResult:
        before_units = self._extract_units(before_text)
        after_units = self._extract_units(after_text)

        before_set = set(before_units)
        after_set = set(after_units)
        removed_candidates = sorted(before_set - after_set)
        added_candidates = sorted(after_set - before_set)

        if method == "rule_based_diff":
            changed, removed, added = self._best_pairing(removed_candidates, added_candidates, threshold=changed_threshold)
        elif method == "keyword":
            changed, removed, added = self._best_pairing_keyword(removed_candidates, added_candidates, threshold=changed_threshold)
        elif method == "tfidf":
            changed, removed, added = self._best_pairing_tfidf(removed_candidates, added_candidates, threshold=changed_threshold)
        else:
            raise ValueError(f"Unsupported baseline method: {method}")

        return TextComparisonResult(removed=removed, added=added, changed=changed)

    def index_document(self, text: str, doc_id: str, version: str):
        if doc_id not in self.documents:
            self.documents[doc_id] = {}
            self.articles[doc_id] = {}
        self.documents[doc_id][version] = text
        self.articles[doc_id][version] = self._split_articles(text)

    def _split_articles(self, text: str) -> Dict[str, str]:
        matches = list(self.ARTICLE_RE.finditer(text))
        articles = {}
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            articles[m.group(1)] = text[start:end].strip()
        return articles

    def search(self, query: str, doc_id: str, top_k: int = 5, version: Optional[str] = None) -> List[BaselineSearchResult]:
        results: List[BaselineSearchResult] = []
        query_words = set(re.findall(r"[^\s\W]+", query.lower(), re.UNICODE))
        for did, versions in self.articles.items():
            if did != doc_id:
                continue
            for ver, articles in versions.items():
                if version and ver != version:
                    continue
                for art_no, content in articles.items():
                    content_lower = content.lower()
                    score = 0.0
                    for word in query_words:
                        score += content_lower.count(word)
                    if len(content.split()) > 0:
                        score = score / (len(content.split()) ** 0.5)
                    if score > 0:
                        results.append(
                            BaselineSearchResult(
                                article_no=art_no,
                                content=content,
                                score=score,
                                version=ver,
                            )
                        )
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def compare(self, doc_id: str, article_no: str) -> List[BaselineChange]:
        v1_articles = self.articles.get(doc_id, {}).get("v1", {})
        v2_articles = self.articles.get(doc_id, {}).get("v2", {})
        v1_text = v1_articles.get(article_no, "")
        v2_text = v2_articles.get(article_no, "")

        if not v1_text and not v2_text:
            return []
        if not v1_text and v2_text:
            return [BaselineChange(article_no=article_no, change_type="added", v1_text="", v2_text=v2_text, similarity=0.0)]
        if v1_text and not v2_text:
            return [BaselineChange(article_no=article_no, change_type="removed", v1_text=v1_text, v2_text="", similarity=0.0)]

        ratio = difflib.SequenceMatcher(None, v1_text, v2_text).ratio()
        if ratio >= 0.999:
            return []
        return [BaselineChange(article_no=article_no, change_type="modified", v1_text=v1_text, v2_text=v2_text, similarity=ratio)]
