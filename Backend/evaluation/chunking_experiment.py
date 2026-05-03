"""
Chunking Experiment: Grid search across chunk sizes, overlaps, and strategies.

Runs 27 configurations (3 sizes × 3 overlaps × 3 strategies) on the evaluation
dataset and produces a comparison JSON + Markdown report.

Usage:
    cd Backend
    python -m evaluation.chunking_experiment
"""

import io
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# ---------------------------------------------------------------------------
# Experiment configuration grid
# ---------------------------------------------------------------------------

CHUNK_SIZES = [256, 512, 1024]       # in tokens
OVERLAP_RATIOS = [0.0, 0.10, 0.20]   # 0%, 10%, 20%
STRATEGIES = ["structural", "recursive", "hybrid"]


@dataclass
class ExperimentConfig:
    chunk_size_tokens: int
    overlap_ratio: float
    strategy: str

    @property
    def chunk_chars(self) -> int:
        return self.chunk_size_tokens * 4

    @property
    def overlap_chars(self) -> int:
        return int(self.chunk_chars * self.overlap_ratio)

    @property
    def label(self) -> str:
        return f"{self.strategy}_s{self.chunk_size_tokens}_o{int(self.overlap_ratio*100)}"


@dataclass
class ConfigResult:
    config_label: str
    strategy: str
    chunk_size_tokens: int
    overlap_pct: int
    total_chunks: int = 0
    avg_chunk_len: float = 0.0
    retrieval_accuracy_top5: float = 0.0
    mrr: float = 0.0
    context_relevance: float = 0.0
    chunk_utilization: float = 0.0
    comparison_f1: float = 0.0
    comparison_precision: float = 0.0
    comparison_recall: float = 0.0
    processing_time: float = 0.0

    def as_dict(self) -> Dict:
        return {
            "config_label": self.config_label,
            "strategy": self.strategy,
            "chunk_size_tokens": self.chunk_size_tokens,
            "overlap_pct": self.overlap_pct,
            "total_chunks": self.total_chunks,
            "avg_chunk_len": round(self.avg_chunk_len, 1),
            "retrieval_accuracy_top5": round(self.retrieval_accuracy_top5, 4),
            "mrr": round(self.mrr, 4),
            "context_relevance": round(self.context_relevance, 4),
            "chunk_utilization": round(self.chunk_utilization, 4),
            "comparison_f1": round(self.comparison_f1, 4),
            "comparison_precision": round(self.comparison_precision, 4),
            "comparison_recall": round(self.comparison_recall, 4),
            "processing_time": round(self.processing_time, 3),
        }


# ---------------------------------------------------------------------------
# Core experiment logic
# ---------------------------------------------------------------------------

def _create_chunker(config: ExperimentConfig):
    """Create a chunker instance for the given config."""
    from src.chunking_strategies import HybridChunker, RecursiveChunker, StructuralChunker

    if config.strategy == "structural":
        return StructuralChunker(max_chars=config.chunk_chars, overlap_chars=config.overlap_chars)
    elif config.strategy == "recursive":
        return RecursiveChunker(max_chars=config.chunk_chars, overlap_chars=config.overlap_chars)
    elif config.strategy == "hybrid":
        return HybridChunker(max_chars=config.chunk_chars, overlap_chars=config.overlap_chars)
    raise ValueError(f"Unknown strategy: {config.strategy}")


def _run_retrieval_test(
    chunks: List,
    embedder,
    query_texts: List[str],
    expected_contents: List[str],
) -> Dict[str, float]:
    """Run retrieval test on chunks using in-memory Qdrant."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    import uuid

    if not chunks or not query_texts:
        return {"accuracy_top5": 0.0, "mrr": 0.0, "context_relevance": 0.0}

    # Build in-memory index
    client = QdrantClient(":memory:")
    collection_name = "chunking_experiment"
    dim = embedder.dim

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    # Embed and index chunks
    chunk_texts = [c.text for c in chunks]
    vectors = embedder.embed(chunk_texts)
    points = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec.tolist(),
                payload={"content": chunk.text, "article_no": chunk.article_no, "index": i},
            )
        )
    client.upsert(collection_name=collection_name, points=points)

    # Run queries
    from evaluation.metrics import context_relevance as calc_context_relevance

    accuracies = []
    rrs = []
    relevances = []

    for query, expected in zip(query_texts, expected_contents):
        qv = embedder.embed_single(query).tolist()
        results = client.query_points(
            collection_name=collection_name,
            query=qv,
            limit=5,
            with_payload=True,
        ).points

        retrieved_texts = [r.payload["content"] for r in results]

        # Top-5 accuracy: any retrieved chunk has significant overlap with expected
        hit = False
        for rt in retrieved_texts:
            overlap = _text_overlap(rt, expected)
            if overlap >= 0.3:
                hit = True
                break
        accuracies.append(1.0 if hit else 0.0)

        # MRR
        rr = 0.0
        for rank, rt in enumerate(retrieved_texts, 1):
            if _text_overlap(rt, expected) >= 0.3:
                rr = 1.0 / rank
                break
        rrs.append(rr)

        # Context relevance
        relevances.append(calc_context_relevance(retrieved_texts, expected))

    client.close()

    return {
        "accuracy_top5": sum(accuracies) / len(accuracies) if accuracies else 0.0,
        "mrr": sum(rrs) / len(rrs) if rrs else 0.0,
        "context_relevance": sum(relevances) / len(relevances) if relevances else 0.0,
    }


def _text_overlap(text_a: str, text_b: str) -> float:
    """Token-level Jaccard overlap."""
    import re
    tokens_a = set(re.findall(r"[^\s\W]+", text_a.lower(), re.UNICODE))
    tokens_b = set(re.findall(r"[^\s\W]+", text_b.lower(), re.UNICODE))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _run_comparison_test(before_chunks: List, after_chunks: List, ground_truth: Dict) -> Dict[str, float]:
    """Run comparison test using existing evaluation logic."""
    import re
    from evaluation.baseline import BaselineSystem
    from evaluation.ground_truth import normalize_text
    from evaluation.metrics import f1_score, precision, recall

    # Extract text units from chunks
    before_units = set()
    for c in before_chunks:
        for line in c.text.splitlines():
            candidate = re.sub(r"\s+", " ", line.strip())
            if candidate:
                before_units.add(candidate)

    after_units = set()
    for c in after_chunks:
        for line in c.text.splitlines():
            candidate = re.sub(r"\s+", " ", line.strip())
            if candidate:
                after_units.add(candidate)

    removed_candidates = sorted(before_units - after_units)
    added_candidates = sorted(after_units - before_units)

    # Pair changes
    import difflib
    matched_removed = set()
    matched_added = set()
    changed = []

    for i, left in enumerate(removed_candidates):
        best_j = -1
        best_score = 0.0
        for j, right in enumerate(added_candidates):
            if j in matched_added:
                continue
            score = difflib.SequenceMatcher(None, left, right).ratio()
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= 0.6:
            matched_removed.add(i)
            matched_added.add(best_j)
            changed.append({"before": left, "after": added_candidates[best_j]})

    predicted_removed = {t for i, t in enumerate(removed_candidates) if i not in matched_removed}
    predicted_added = {t for i, t in enumerate(added_candidates) if i not in matched_added}
    predicted_changed = {(normalize_text(c["before"]), normalize_text(c["after"])) for c in changed}

    actual_removed = set(ground_truth.get("removed", []))
    actual_added = set(ground_truth.get("added", []))
    actual_changed_items = ground_truth.get("changed", [])
    actual_changed = set()
    for item in actual_changed_items:
        b = normalize_text(item.get("before", ""))
        a = normalize_text(item.get("after", ""))
        if b or a:
            actual_changed.add((b, a))

    # Calculate metrics
    tp = (len(predicted_removed & actual_removed)
          + len(predicted_added & actual_added)
          + len(predicted_changed & actual_changed))
    fp = (len(predicted_removed - actual_removed)
          + len(predicted_added - actual_added)
          + len(predicted_changed - actual_changed))
    fn = (len(actual_removed - predicted_removed)
          + len(actual_added - predicted_added)
          + len(actual_changed - predicted_changed))

    p = precision(tp, fp)
    r = recall(tp, fn)
    f1 = f1_score(p, r)

    return {"precision": p, "recall": r, "f1": f1}


def _build_queries_from_gt(ground_truth: Dict) -> Tuple[List[str], List[str]]:
    """Build retrieval query/expected pairs from ground truth."""
    queries = []
    expected = []

    for item in ground_truth.get("removed", []):
        if item.strip():
            queries.append(item[:200])  # Use first 200 chars as query
            expected.append(item)

    for item in ground_truth.get("added", []):
        if item.strip():
            queries.append(item[:200])
            expected.append(item)

    for item in ground_truth.get("changed", []):
        before = item.get("before", "")
        after = item.get("after", "")
        if before.strip():
            queries.append(before[:200])
            expected.append(before)
        if after.strip():
            queries.append(after[:200])
            expected.append(after)

    return queries, expected


def run_single_config(config: ExperimentConfig, cases: List[Dict], embedder) -> ConfigResult:
    """Run experiment for a single configuration across all cases."""
    t0 = time.time()
    chunker = _create_chunker(config)

    all_chunks_count = 0
    all_chunk_lengths = []
    all_retrieval = {"accuracy_top5": [], "mrr": [], "context_relevance": []}
    all_comparison = {"precision": [], "recall": [], "f1": []}
    all_chunk_texts_for_util = []
    all_reference_texts = []

    for case in cases:
        before_text = case["before_text"]
        after_text = case["after_text"]
        gt = case["ground_truth"]

        # Chunk
        before_chunks = chunker.chunk_text(before_text, doc_id=f"exp_before_{case['case_id']}", version="v1")
        after_chunks = chunker.chunk_text(after_text, doc_id=f"exp_after_{case['case_id']}", version="v2")

        all_chunks = before_chunks + after_chunks
        all_chunks_count += len(all_chunks)
        all_chunk_lengths.extend([len(c.text) for c in all_chunks])

        # Retrieval test
        queries, expected = _build_queries_from_gt(gt)
        if queries:
            retrieval_result = _run_retrieval_test(all_chunks, embedder, queries, expected)
            all_retrieval["accuracy_top5"].append(retrieval_result["accuracy_top5"])
            all_retrieval["mrr"].append(retrieval_result["mrr"])
            all_retrieval["context_relevance"].append(retrieval_result["context_relevance"])

        # Comparison test
        comp_result = _run_comparison_test(before_chunks, after_chunks, gt)
        all_comparison["precision"].append(comp_result["precision"])
        all_comparison["recall"].append(comp_result["recall"])
        all_comparison["f1"].append(comp_result["f1"])

        # Collect for chunk_utilization
        all_chunk_texts_for_util.extend([c.text for c in all_chunks])
        all_reference_texts.extend(gt.get("removed", []))
        all_reference_texts.extend(gt.get("added", []))
        for ch in gt.get("changed", []):
            all_reference_texts.append(ch.get("before", ""))
            all_reference_texts.append(ch.get("after", ""))

    processing_time = time.time() - t0

    from evaluation.metrics import chunk_utilization as calc_chunk_util

    return ConfigResult(
        config_label=config.label,
        strategy=config.strategy,
        chunk_size_tokens=config.chunk_size_tokens,
        overlap_pct=int(config.overlap_ratio * 100),
        total_chunks=all_chunks_count,
        avg_chunk_len=sum(all_chunk_lengths) / len(all_chunk_lengths) if all_chunk_lengths else 0,
        retrieval_accuracy_top5=_avg(all_retrieval["accuracy_top5"]),
        mrr=_avg(all_retrieval["mrr"]),
        context_relevance=_avg(all_retrieval["context_relevance"]),
        chunk_utilization=calc_chunk_util(all_chunk_texts_for_util, [r for r in all_reference_texts if r]),
        comparison_f1=_avg(all_comparison["f1"]),
        comparison_precision=_avg(all_comparison["precision"]),
        comparison_recall=_avg(all_comparison["recall"]),
        processing_time=processing_time,
    )


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_markdown_report(results: List[ConfigResult], best_config: ConfigResult) -> str:
    """Generate a Markdown comparison report."""
    lines = [
        "# Chunking Strategy Experiment Report",
        "",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total configurations tested**: {len(results)}",
        f"**Grid**: chunk_sizes={CHUNK_SIZES} × overlaps={[int(o*100) for o in OVERLAP_RATIOS]}% × strategies={STRATEGIES}",
        "",
        "---",
        "",
        "## 1. Bảng so sánh các cấu hình",
        "",
        "| # | Config | Strategy | Size (tokens) | Overlap | Chunks | Avg Len | Ret. Acc@5 | MRR | Context Rel. | Chunk Util. | Comp. F1 | Time (s) |",
        "|---|--------|----------|---------------|---------|--------|---------|------------|-----|-------------|-------------|----------|----------|",
    ]

    sorted_results = sorted(results, key=lambda r: r.comparison_f1, reverse=True)
    for i, r in enumerate(sorted_results, 1):
        mark = " ⭐" if r.config_label == best_config.config_label else ""
        lines.append(
            f"| {i} | {r.config_label}{mark} | {r.strategy} | {r.chunk_size_tokens} | {r.overlap_pct}% | "
            f"{r.total_chunks} | {r.avg_chunk_len:.0f} | {r.retrieval_accuracy_top5:.4f} | {r.mrr:.4f} | "
            f"{r.context_relevance:.4f} | {r.chunk_utilization:.4f} | {r.comparison_f1:.4f} | {r.processing_time:.1f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Cấu hình tối ưu được chọn",
        "",
        f"**{best_config.config_label}** ⭐",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Strategy | {best_config.strategy} |",
        f"| Chunk Size | {best_config.chunk_size_tokens} tokens ({best_config.chunk_size_tokens * 4} chars) |",
        f"| Overlap | {best_config.overlap_pct}% |",
        f"| Total Chunks | {best_config.total_chunks} |",
        f"| Avg Chunk Length | {best_config.avg_chunk_len:.0f} chars |",
        f"| Retrieval Accuracy @5 | {best_config.retrieval_accuracy_top5:.4f} |",
        f"| MRR | {best_config.mrr:.4f} |",
        f"| Context Relevance | {best_config.context_relevance:.4f} |",
        f"| Chunk Utilization | {best_config.chunk_utilization:.4f} |",
        f"| Comparison F1 | {best_config.comparison_f1:.4f} |",
        f"| Processing Time | {best_config.processing_time:.1f}s |",
        "",
        "---",
        "",
        "## 3. Phân tích theo factor",
        "",
    ])

    # Analyze by strategy
    lines.extend(["### 3.1. Theo Strategy", ""])
    lines.append("| Strategy | Avg Ret. Acc@5 | Avg MRR | Avg Context Rel. | Avg Comp. F1 | Avg Chunks |")
    lines.append("|----------|---------------|---------|------------------|-------------|------------|")
    for strategy in STRATEGIES:
        subset = [r for r in results if r.strategy == strategy]
        lines.append(
            f"| {strategy} | {_avg([r.retrieval_accuracy_top5 for r in subset]):.4f} | "
            f"{_avg([r.mrr for r in subset]):.4f} | "
            f"{_avg([r.context_relevance for r in subset]):.4f} | "
            f"{_avg([r.comparison_f1 for r in subset]):.4f} | "
            f"{_avg([r.total_chunks for r in subset]):.0f} |"
        )

    # Analyze by chunk size
    lines.extend(["", "### 3.2. Theo Chunk Size", ""])
    lines.append("| Size (tokens) | Avg Ret. Acc@5 | Avg MRR | Avg Context Rel. | Avg Comp. F1 | Avg Chunks |")
    lines.append("|--------------|---------------|---------|------------------|-------------|------------|")
    for size in CHUNK_SIZES:
        subset = [r for r in results if r.chunk_size_tokens == size]
        lines.append(
            f"| {size} | {_avg([r.retrieval_accuracy_top5 for r in subset]):.4f} | "
            f"{_avg([r.mrr for r in subset]):.4f} | "
            f"{_avg([r.context_relevance for r in subset]):.4f} | "
            f"{_avg([r.comparison_f1 for r in subset]):.4f} | "
            f"{_avg([r.total_chunks for r in subset]):.0f} |"
        )

    # Analyze by overlap
    lines.extend(["", "### 3.3. Theo Overlap", ""])
    lines.append("| Overlap | Avg Ret. Acc@5 | Avg MRR | Avg Context Rel. | Avg Comp. F1 | Avg Chunks |")
    lines.append("|---------|---------------|---------|------------------|-------------|------------|")
    for overlap in OVERLAP_RATIOS:
        pct = int(overlap * 100)
        subset = [r for r in results if r.overlap_pct == pct]
        lines.append(
            f"| {pct}% | {_avg([r.retrieval_accuracy_top5 for r in subset]):.4f} | "
            f"{_avg([r.mrr for r in subset]):.4f} | "
            f"{_avg([r.context_relevance for r in subset]):.4f} | "
            f"{_avg([r.comparison_f1 for r in subset]):.4f} | "
            f"{_avg([r.total_chunks for r in subset]):.0f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Kết luận",
        "",
        f"Cấu hình **{best_config.config_label}** cho kết quả tốt nhất với:",
        f"- Comparison F1 = **{best_config.comparison_f1:.4f}**",
        f"- Retrieval Accuracy @5 = **{best_config.retrieval_accuracy_top5:.4f}**",
        f"- MRR = **{best_config.mrr:.4f}**",
        f"- Context Relevance = **{best_config.context_relevance:.4f}**",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_chunking_experiment() -> Dict:
    """Run the full chunking experiment."""
    from src.embedder import LegalEmbedder
    from config import settings
    from evaluation.ground_truth import load_evalution_dataset

    print("=" * 60)
    print("  CHUNKING STRATEGY EXPERIMENT")
    print("=" * 60)

    # Load dataset
    print("\n[1/4] Loading evaluation dataset...")
    cases = load_evalution_dataset()
    if not cases:
        raise ValueError("No evaluation cases found in evalution_dataset/")
    print(f"  Loaded {len(cases)} cases")

    # Load embedder (shared across all configs to save time)
    print("\n[2/4] Loading embedding model...")
    embedder = LegalEmbedder(settings.EMBEDDING_MODEL)

    # Build config grid
    configs = []
    for size in CHUNK_SIZES:
        for overlap in OVERLAP_RATIOS:
            for strategy in STRATEGIES:
                configs.append(ExperimentConfig(
                    chunk_size_tokens=size,
                    overlap_ratio=overlap,
                    strategy=strategy,
                ))
    print(f"\n[3/4] Running {len(configs)} configurations...")

    # Run experiments
    results: List[ConfigResult] = []
    for i, config in enumerate(configs, 1):
        print(f"\n  [{i}/{len(configs)}] {config.label}...", end=" ", flush=True)
        try:
            result = run_single_config(config, cases, embedder)
            results.append(result)
            print(f"F1={result.comparison_f1:.4f}  RetAcc={result.retrieval_accuracy_top5:.4f}  "
                  f"MRR={result.mrr:.4f}  Chunks={result.total_chunks}  Time={result.processing_time:.1f}s")
        except Exception as e:
            print(f"ERROR: {e}")

    if not results:
        raise RuntimeError("No results collected. Check errors above.")

    # Find best config (weighted score: 50% comparison_f1 + 30% retrieval_acc + 20% mrr)
    def score(r: ConfigResult) -> float:
        return 0.50 * r.comparison_f1 + 0.30 * r.retrieval_accuracy_top5 + 0.20 * r.mrr

    best = max(results, key=score)

    # Save results
    print(f"\n[4/4] Saving results...")
    output_dir = PROJECT_ROOT / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "num_configs": len(results),
        "num_cases": len(cases),
        "grid": {
            "chunk_sizes": CHUNK_SIZES,
            "overlap_ratios": [int(o * 100) for o in OVERLAP_RATIOS],
            "strategies": STRATEGIES,
        },
        "best_config": best.as_dict(),
        "scoring_formula": "0.50 * comparison_f1 + 0.30 * retrieval_accuracy_top5 + 0.20 * mrr",
        "results": [r.as_dict() for r in results],
    }
    json_path = output_dir / "chunking_experiment_results.json"
    json_path.write_text(json.dumps(json_output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON: {json_path}")

    # Markdown report
    md_report = generate_markdown_report(results, best)
    md_path = output_dir / "chunking_report.md"
    md_path.write_text(md_report, encoding="utf-8")
    print(f"  Report: {md_path}")

    print(f"\n{'=' * 60}")
    print(f"  BEST CONFIG: {best.config_label}")
    print(f"  Comparison F1: {best.comparison_f1:.4f}")
    print(f"  Retrieval Accuracy @5: {best.retrieval_accuracy_top5:.4f}")
    print(f"  MRR: {best.mrr:.4f}")
    print(f"  Weighted Score: {score(best):.4f}")
    print(f"{'=' * 60}\n")

    return json_output


def main():
    run_chunking_experiment()


if __name__ == "__main__":
    main()
