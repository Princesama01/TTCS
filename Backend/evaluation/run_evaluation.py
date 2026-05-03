import io
import json
import os
import sys
import time
from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from api.ollama_client import OllamaClient
from api.services.compare_pipeline_service import run_llm_compare, split_sentences
from config import settings
from src.embedder import LegalEmbedder
from evaluation.baseline import BaselineSystem, TextComparisonResult
from evaluation.ground_truth import load_evalution_dataset, normalize_text
from evaluation.metrics import f1_score, precision, recall

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BASELINE_METHOD = os.getenv("EVAL_BASELINE_METHOD", "rule_based_diff").strip().lower()
RAG_MAX_SEGMENTS = int(os.getenv("EVAL_RAG_MAX_SEGMENTS", "700"))
RAG_MAX_SEGMENTS = max(120, min(RAG_MAX_SEGMENTS, 1200))


@dataclass
class CountMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def as_dict(self) -> Dict[str, float]:
        p = precision(self.tp, self.fp)
        r = recall(self.tp, self.fn)
        return {
            "precision": p,
            "recall": r,
            "f1": f1_score(p, r),
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
        }


def _tokenize(text: str) -> Set[str]:
    return set(part for part in normalize_text(text).lower().split(" ") if part)


def _text_similarity(left: str, right: str) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    seq = SequenceMatcher(None, left_norm, right_norm).ratio()
    lt = _tokenize(left_norm)
    rt = _tokenize(right_norm)
    union = len(lt | rt)
    jaccard = (len(lt & rt) / union) if union else 0.0
    return max(seq, jaccard)


def _merge_changed_segments(segments_changed: List[Dict]) -> List[Dict]:
    def _is_mergeable_fragment(text: str) -> bool:
        t = normalize_text(text)
        if not t:
            return True
        if len(t) <= 36:
            return True
        if SequenceMatcher(None, t, t.upper()).ratio() > 0.98:
            return True
        if t.rstrip(".").replace("/", "").replace("-", "").replace(" ", "").isdigit():
            return True
        return False

    merged: List[Dict] = []
    for seg in segments_changed:
        verdict = seg.get("verdict")
        source = normalize_text(seg.get("source") or "")
        target = normalize_text(seg.get("target") or "")
        if verdict not in {"removed", "added", "changed_meaning"}:
            continue
        if verdict == "removed" and not source:
            continue
        if verdict == "added" and not target:
            continue
        if verdict == "changed_meaning" and not (source and target):
            continue

        normalized = {
            "verdict": verdict,
            "source": source,
            "target": target,
            "confidence": float(seg.get("confidence") or 0.0),
        }
        if not merged:
            merged.append(normalized)
            continue

        prev = merged[-1]
        can_merge = prev["verdict"] == normalized["verdict"]
        if can_merge and normalized["verdict"] == "removed":
            if _is_mergeable_fragment(prev["source"]) and _is_mergeable_fragment(normalized["source"]):
                prev["source"] = normalize_text(f"{prev['source']} {normalized['source']}")
                prev["confidence"] = max(prev["confidence"], normalized["confidence"])
            else:
                merged.append(normalized)
        elif can_merge and normalized["verdict"] == "added":
            if _is_mergeable_fragment(prev["target"]) and _is_mergeable_fragment(normalized["target"]):
                prev["target"] = normalize_text(f"{prev['target']} {normalized['target']}")
                prev["confidence"] = max(prev["confidence"], normalized["confidence"])
            else:
                merged.append(normalized)
        elif can_merge and normalized["verdict"] == "changed_meaning":
            merged.append(normalized)
        else:
            merged.append(normalized)

    return merged


def _convert_added_removed_to_changed(removed: List[str], added: List[str], threshold: float = 0.82) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    if not removed or not added:
        return [], removed, added

    matched_removed = set()
    matched_added = set()
    changed: List[Dict[str, str]] = []

    for i, source in enumerate(removed):
        best_j = -1
        best_score = 0.0
        for j, target in enumerate(added):
            if j in matched_added:
                continue
            score = _text_similarity(source, target)
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= threshold:
            matched_removed.add(i)
            matched_added.add(best_j)
            changed.append({"before": source, "after": added[best_j], "similarity": round(best_score, 4)})

    rem_rest = [text for idx, text in enumerate(removed) if idx not in matched_removed]
    add_rest = [text for idx, text in enumerate(added) if idx not in matched_added]
    return changed, rem_rest, add_rest


def _rag_compare(ollama: OllamaClient, embedder: LegalEmbedder, before_text: str, after_text: str) -> TextComparisonResult:
    s1_len = len(split_sentences(before_text, max_segments=10000))
    s2_len = len(split_sentences(after_text, max_segments=10000))
    max_segments = min(max(s1_len, s2_len, 120), RAG_MAX_SEGMENTS)

    result = run_llm_compare(
        ollama=ollama,
        embedder=embedder,
        text_1=before_text,
        text_2=after_text,
        llm_confidence_threshold=0.70,
        semantic_threshold=0.88,
        candidate_threshold=0.60,
        max_segments=max_segments,
    )
    merged = _merge_changed_segments(result.get("segments_changed", []))
    removed: List[str] = [seg["source"] for seg in merged if seg["verdict"] == "removed"]
    added: List[str] = [seg["target"] for seg in merged if seg["verdict"] == "added"]
    changed: List[Dict[str, str]] = [
        {"before": seg["source"], "after": seg["target"], "similarity": round(float(seg.get("confidence") or 0.0), 4)}
        for seg in merged
        if seg["verdict"] == "changed_meaning"
    ]

    inferred_changed, removed, added = _convert_added_removed_to_changed(removed, added, threshold=0.72)
    changed.extend(inferred_changed)

    return TextComparisonResult(
        removed=sorted(set(removed)),
        added=sorted(set(added)),
        changed=changed,
    )


def _changed_pairs(changed_items: List[Dict[str, str]]) -> Set[Tuple[str, str]]:
    pairs = set()
    for item in changed_items:
        before = normalize_text(item.get("before", ""))
        after = normalize_text(item.get("after", ""))
        if before or after:
            pairs.add((before, after))
    return pairs


def _score_type(predicted: Set, actual: Set) -> CountMetrics:
    return CountMetrics(
        tp=len(predicted & actual),
        fp=len(predicted - actual),
        fn=len(actual - predicted),
    )


def _evaluate_case(prediction: TextComparisonResult, ground_truth: Dict) -> Dict:
    predicted_removed = set(prediction.removed)
    predicted_added = set(prediction.added)
    predicted_changed = _changed_pairs(prediction.changed)

    actual_removed = set(ground_truth.get("removed", []))
    actual_added = set(ground_truth.get("added", []))
    actual_changed = _changed_pairs(ground_truth.get("changed", []))

    removed_metrics = _score_type(predicted_removed, actual_removed)
    added_metrics = _score_type(predicted_added, actual_added)
    changed_metrics = _score_type(predicted_changed, actual_changed)

    return {
        "removed": removed_metrics,
        "added": added_metrics,
        "changed": changed_metrics,
        "predicted_counts": {
            "removed": len(predicted_removed),
            "added": len(predicted_added),
            "changed": len(predicted_changed),
        },
        "ground_truth_counts": {
            "removed": len(actual_removed),
            "added": len(actual_added),
            "changed": len(actual_changed),
        },
    }


def _evaluate_system(cases: List[Dict], mode: str, ollama: OllamaClient, embedder: LegalEmbedder) -> Dict:
    removed_total = CountMetrics()
    added_total = CountMetrics()
    changed_total = CountMetrics()
    per_case: List[Dict] = []
    baseline = BaselineSystem()

    for case in cases:
        if mode == "baseline":
            if BASELINE_METHOD == "rule_based_diff":
                threshold = 0.8
            elif BASELINE_METHOD == "keyword":
                threshold = 0.4
            elif BASELINE_METHOD == "tfidf":
                threshold = 0.45
            else:
                raise ValueError(f"Unsupported baseline method: {BASELINE_METHOD}")
            prediction = baseline.compare_texts(
                case["before_text"],
                case["after_text"],
                method=BASELINE_METHOD,
                changed_threshold=threshold,
            )
        else:
            prediction = _rag_compare(ollama=ollama, embedder=embedder, before_text=case["before_text"], after_text=case["after_text"])

        case_score = _evaluate_case(prediction, case["ground_truth"])
        removed_total.tp += case_score["removed"].tp
        removed_total.fp += case_score["removed"].fp
        removed_total.fn += case_score["removed"].fn
        added_total.tp += case_score["added"].tp
        added_total.fp += case_score["added"].fp
        added_total.fn += case_score["added"].fn
        changed_total.tp += case_score["changed"].tp
        changed_total.fp += case_score["changed"].fp
        changed_total.fn += case_score["changed"].fn

        per_case.append(
            {
                "case_id": case["case_id"],
                "metrics": {
                    "removed": case_score["removed"].as_dict(),
                    "added": case_score["added"].as_dict(),
                    "changed": case_score["changed"].as_dict(),
                },
                "predicted_counts": case_score["predicted_counts"],
                "ground_truth_counts": case_score["ground_truth_counts"],
            }
        )

    overall = CountMetrics(
        tp=removed_total.tp + added_total.tp + changed_total.tp,
        fp=removed_total.fp + added_total.fp + changed_total.fp,
        fn=removed_total.fn + added_total.fn + changed_total.fn,
    )

    return {
        "comparison_metrics": {
            "removed": removed_total.as_dict(),
            "added": added_total.as_dict(),
            "changed": changed_total.as_dict(),
            "overall": overall.as_dict(),
            "num_cases": len(cases),
        },
        "per_case": per_case,
    }


def run_evaluation() -> Dict:
    cases = load_evalution_dataset()
    if not cases:
        raise ValueError("Khong tim thay dataset hop le trong thu muc evalution_dataset.")

    ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL, model_name=settings.OLLAMA_MODEL)
    embedder = LegalEmbedder(settings.EMBEDDING_MODEL)

    baseline_result = _evaluate_system(cases, mode="baseline", ollama=ollama, embedder=embedder)
    rag_result = _evaluate_system(cases, mode="rag", ollama=ollama, embedder=embedder)

    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "baseline_method": BASELINE_METHOD,
            "rag_mode": "difflib_semantic_llm",
            "semantic_threshold": 0.88,
            "candidate_threshold": 0.60,
            "llm_confidence_threshold": 0.70,
            "max_segments": RAG_MAX_SEGMENTS,
            "ollama_model": settings.OLLAMA_MODEL,
            "postprocess_merge_segments": True,
            "postprocess_added_removed_to_changed": True,
        },
        "rag": rag_result,
        "baseline": baseline_result,
    }

    output_dir = PROJECT_ROOT / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation_results.json"
    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def main():
    output = run_evaluation()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
