from typing import Dict, List, Set, Tuple
import re


def precision(true_positives: int, false_positives: int) -> float:
    if true_positives + false_positives == 0:
        return 0.0
    return true_positives / (true_positives + false_positives)


def recall(true_positives: int, false_negatives: int) -> float:
    if true_positives + false_negatives == 0:
        return 0.0
    return true_positives / (true_positives + false_negatives)


def f1_score(prec: float, rec: float) -> float:
    if prec + rec == 0:
        return 0.0
    return 2 * (prec * rec) / (prec + rec)


def compute_classification_metrics(predicted: Set, actual: Set) -> Tuple[float, float, float]:
    tp = len(predicted & actual)
    fp = len(predicted - actual)
    fn = len(actual - predicted)
    p = precision(tp, fp)
    r = recall(tp, fn)
    f = f1_score(p, r)
    return p, r, f


def top_k_accuracy(retrieved_articles: List[str], expected_articles: List[str], k: int = 5) -> float:
    return 1.0 if set(retrieved_articles[:k]) & set(expected_articles) else 0.0


def top_k_precision(retrieved_articles: List[str], expected_articles: List[str], k: int = 5) -> float:
    top_k = retrieved_articles[:k]
    if not top_k:
        return 0.0
    expected = set(expected_articles)
    return sum(1 for a in top_k if a in expected) / len(top_k)


def reciprocal_rank(retrieved_articles: List[str], expected_articles: List[str]) -> float:
    expected = set(expected_articles)
    for i, article in enumerate(retrieved_articles, 1):
        if article in expected:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(all_retrieved: List[List[str]], all_expected: List[List[str]]) -> float:
    if not all_retrieved:
        return 0.0
    total = sum(reciprocal_rank(retrieved, expected) for retrieved, expected in zip(all_retrieved, all_expected))
    return total / len(all_retrieved)


def change_detection_accuracy(predicted_changes: Dict[str, bool], actual_changes: Dict[str, bool]) -> Tuple[float, float, float]:
    predicted = {art for art, changed in predicted_changes.items() if changed}
    actual = {art for art, changed in actual_changes.items() if changed}
    return compute_classification_metrics(predicted, actual)


def change_type_accuracy(predicted_types: Dict[str, Set[str]], actual_types: Dict[str, Set[str]]) -> Dict[str, Tuple[float, float, float]]:
    all_types = {"added", "removed", "modified"}
    results = {}
    for change_type in all_types:
        predicted = {art for art, types in predicted_types.items() if change_type in types}
        actual = {art for art, types in actual_types.items() if change_type in types}
        results[change_type] = compute_classification_metrics(predicted, actual)
    return results


def overall_change_type_accuracy(predicted_types: Dict[str, Set[str]], actual_types: Dict[str, Set[str]]) -> Tuple[float, float, float]:
    predicted_pairs = {(art, t) for art, types in predicted_types.items() for t in types}
    actual_pairs = {(art, t) for art, types in actual_types.items() for t in types}
    return compute_classification_metrics(predicted_pairs, actual_pairs)


def context_relevance(retrieved_texts: List[str], expected_text: str) -> float:
    """
    Estimate relevance by maximum token-overlap ratio between expected text
    and any retrieved chunk.
    """
    expected_tokens = set(re.findall(r"[^\s\W]+", (expected_text or "").lower(), re.UNICODE))
    if not expected_tokens or not retrieved_texts:
        return 0.0
    best = 0.0
    for text in retrieved_texts:
        tokens = set(re.findall(r"[^\s\W]+", (text or "").lower(), re.UNICODE))
        if not tokens:
            continue
        overlap = len(expected_tokens & tokens) / len(expected_tokens)
        if overlap > best:
            best = overlap
    return best


def chunk_utilization(chunks: List[str], reference_texts: List[str], threshold: float = 0.1) -> float:
    """
    Fraction of chunks considered useful, where a useful chunk has enough token
    overlap with at least one reference text.
    """
    if not chunks:
        return 0.0
    ref_tokens = []
    for ref in reference_texts:
        tokens = set(re.findall(r"[^\s\W]+", (ref or "").lower(), re.UNICODE))
        if tokens:
            ref_tokens.append(tokens)
    if not ref_tokens:
        return 0.0

    useful = 0
    for chunk in chunks:
        chunk_tokens = set(re.findall(r"[^\s\W]+", (chunk or "").lower(), re.UNICODE))
        if not chunk_tokens:
            continue
        max_overlap = 0.0
        for rt in ref_tokens:
            overlap = len(chunk_tokens & rt) / len(chunk_tokens)
            if overlap > max_overlap:
                max_overlap = overlap
        if max_overlap >= threshold:
            useful += 1
    return useful / len(chunks)
