import json
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

import numpy as np

_ABBR_RE = re.compile(r"\b(TP|TS|ThS|PGS|GS|Mr|Mrs|Ms|Dr|No)\.$", re.IGNORECASE)
_PUNCT_EDGE_RE = re.compile(r"^[\s\-\–\—\•\·\(\)\[\]\"“”'`]+|[\s\-\–\—\•\·\(\)\[\]\"“”'`]+$")
_SPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-zA-Z0-9À-ỹ_]+", re.UNICODE)

# Terms that often change legal intent if added/removed/replaced.
_CRITICAL_TERMS = [
    "nhượng quyền",
    "độc quyền",
    "không độc quyền",
    "bồi thường",
    "phạt",
    "vi phạm",
    "chấm dứt",
    "hủy bỏ",
    "thanh toán",
    "miễn thanh toán",
    "gia hạn",
    "chuyển nhượng",
    "bảo mật",
    "sở hữu trí tuệ",
    "đặt cọc",
    "đảm bảo",
    "nghĩa vụ",
    "quyền",
    "trách nhiệm",
    "điều kiện",
]
_NEGATION_TERMS = ["không", "chưa", "không được", "miễn", "cấm", "phải"]


def normalize_sentence(text: str) -> str:
    s = text.strip()
    s = _SPACE_RE.sub(" ", s)
    s = _PUNCT_EDGE_RE.sub("", s)
    return s


def split_sentences(text: str, max_segments: int = 120) -> List[str]:
    if not text or not text.strip():
        return []

    lines = [ln.strip() for ln in text.splitlines()]
    raw_candidates = []
    for ln in lines:
        if not ln:
            continue
        if re.match(r"^(\-|\*|\u2022|\d+\.)\s+", ln):
            raw_candidates.append(ln)
            continue
        parts = re.split(r"(?<=[\.\!\?;:])\s+", ln)
        raw_candidates.extend(parts)

    merged = []
    for part in raw_candidates:
        p = normalize_sentence(part)
        if not p:
            continue
        if merged and _ABBR_RE.search(merged[-1]):
            merged[-1] = f"{merged[-1]} {p}".strip()
        else:
            merged.append(p)
    return merged[:max_segments]


def _lexical_ratio(a: str, b: str) -> float:
    return float(SequenceMatcher(None, a, b).ratio())


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _token_overlap(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return float(len(ta.intersection(tb)) / len(ta.union(tb)))


def _extract_critical_terms(text: str) -> set:
    normalized = normalize_sentence(text).lower()
    found = set()
    for term in _CRITICAL_TERMS + _NEGATION_TERMS:
        if term in normalized:
            found.add(term)
    return found


def _critical_delta(source: str, target: str) -> dict:
    src_terms = _extract_critical_terms(source)
    tgt_terms = _extract_critical_terms(target)
    removed = sorted(src_terms - tgt_terms)
    added = sorted(tgt_terms - src_terms)
    changed = bool(removed or added)
    return {
        "changed": changed,
        "removed": removed,
        "added": added,
        "source_terms": sorted(src_terms),
        "target_terms": sorted(tgt_terms),
    }


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _build_similarity_matrix(emb_1: np.ndarray, emb_2: np.ndarray) -> np.ndarray:
    matrix = np.zeros((len(emb_1), len(emb_2)), dtype=float)
    for i in range(len(emb_1)):
        for j in range(len(emb_2)):
            matrix[i, j] = _cosine(emb_1[i], emb_2[j])
    return matrix


def align_sentence_pairs(
    sentences_1: List[str],
    sentences_2: List[str],
    matrix: np.ndarray,
    candidate_threshold: float,
    max_jump: int = 6,
    lexical_min: float = 0.12,
    token_overlap_min: float = 0.18,
) -> Tuple[List[dict], set, set]:
    candidates = []
    if not sentences_1 or not sentences_2:
        return [], set(), set()

    ratio = len(sentences_2) / max(1, len(sentences_1))
    window = max(3, int(abs(len(sentences_1) - len(sentences_2)) * 0.5) + 3)

    for i in range(len(sentences_1)):
        expected_j = int(i * ratio)
        j_min = max(0, expected_j - window)
        j_max = min(len(sentences_2) - 1, expected_j + window)
        for j in range(j_min, j_max + 1):
            score = float(matrix[i, j])
            lex = _lexical_ratio(sentences_1[i], sentences_2[j])
            tok = _token_overlap(sentences_1[i], sentences_2[j])
            if score < candidate_threshold:
                continue
            if lex < lexical_min and tok < token_overlap_min:
                continue
            pos_penalty = abs(i - j) * 0.012
            adj_score = max(0.0, score - pos_penalty)
            candidates.append((adj_score, score, lex, tok, i, j))

    candidates.sort(reverse=True, key=lambda x: x[0])

    used_i = set()
    used_j = set()
    pairs = []
    last_i = -1
    last_j = -1
    for adj_score, score, lex, tok, i, j in candidates:
        if i in used_i or j in used_j:
            continue
        if last_i >= 0 and (i < last_i or j < last_j):
            continue
        if last_i >= 0 and (abs(i - last_i) > max_jump or abs(j - last_j) > max_jump):
            continue
        used_i.add(i)
        used_j.add(j)
        last_i, last_j = i, j
        pairs.append(
            {
                "source": sentences_1[i],
                "target": sentences_2[j],
                "similarity": round(score, 4),
                "adjusted_similarity": round(adj_score, 4),
                "lexical_similarity": round(lex, 4),
                "token_overlap": round(tok, 4),
                "source_index": i,
                "target_index": j,
            }
        )
    return pairs, used_i, used_j


def _semantic_verdict(pair: dict, semantic_threshold: float) -> Tuple[str, float, str]:
    sim = float(pair["similarity"])
    lex = float(pair.get("lexical_similarity", 0.0))
    tok = float(pair.get("token_overlap", 0.0))
    cdelta = _critical_delta(pair["source"], pair["target"])

    if cdelta["changed"]:
        return "changed_meaning", sim, "critical legal terms changed"

    if sim >= semantic_threshold or lex >= 0.985:
        return "equivalent", max(sim, lex), "high sentence-level semantic/lexical similarity"

    low_threshold = max(0.5, semantic_threshold - 0.12)
    if sim < low_threshold and tok < 0.35:
        return "changed_meaning", sim, "semantic similarity below low threshold"

    if (lex >= 0.94 and sim >= semantic_threshold - 0.08) or (tok >= 0.72 and sim >= semantic_threshold - 0.1):
        return "equivalent", max(sim, lex, tok), "minor wording difference with similar intent"

    return "changed_meaning", sim, "borderline semantic similarity classified as changed"


def _extract_json(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain JSON object")
    return json.loads(text[start : end + 1])


def _judge_pair_with_llm(ollama, source: str, target: str) -> dict:
    prompt = (
        "Bạn là bộ chấm semantic equivalence cho văn bản pháp lý tiếng Việt.\n"
        "Nhiệm vụ: chỉ kết luận CHANGED_MEANING khi nghĩa vụ/quyền/điều kiện/phạm vi trách nhiệm thay đổi thực chất.\n"
        "Ưu tiên phân loại EQUIVALENT cho các trường hợp chỉ khác cách diễn đạt, trật tự câu, từ đồng nghĩa pháp lý, chuẩn hóa hoa-thường, hoặc đổi cụm từ nhưng không đổi nội dung pháp lý.\n"
        "Ví dụ thường là EQUIVALENT: 'trong thời hạn hợp đồng có hiệu lực' ~ 'trong thời gian hợp đồng còn hiệu lực'; "
        "'được quyền' ~ 'có quyền'; 'tiến hành' ~ 'triển khai'; 'như đã nêu tại Điều 1' ~ 'quy định tại Điều 1'.\n"
        "Chỉ chọn CHANGED_MEANING nếu có khác biệt thực chất về: có/không nghĩa vụ, mức độ bắt buộc, đối tượng, phạm vi, thời hạn, điều kiện kích hoạt, chế tài.\n\n"
        "Trả về JSON duy nhất theo format:\n"
        '{ "verdict": "equivalent|changed_meaning", "confidence": 0.0-1.0, "reason": "ngắn gọn, nêu điểm khác biệt thực chất nếu có" }\n\n'
        f"SOURCE: {source}\n"
        f"TARGET: {target}"
    )
    raw = ollama.generate(prompt=prompt, system="Output JSON only.")
    data = _extract_json(raw)
    verdict = data.get("verdict", "changed_meaning")
    confidence = float(data.get("confidence", 0.0))
    reason = data.get("reason", "")
    if verdict not in ["equivalent", "changed_meaning"]:
        verdict = "changed_meaning"
    return {"verdict": verdict, "confidence": confidence, "reason": reason}


def _blank_critical_delta() -> dict:
    return {"changed": False, "removed": [], "added": [], "source_terms": [], "target_terms": []}


def _new_summary() -> Dict[str, int]:
    return {"equivalent": 0, "changed_meaning": 0, "added": 0, "removed": 0}


def _add_segment(segments: List[dict], summary: Dict[str, int], segment: dict) -> None:
    verdict = segment.get("verdict")
    if verdict in summary:
        summary[verdict] += 1
    segments.append(segment)


def _build_difflib_stage_output(sentences_1: List[str], sentences_2: List[str], opcodes: List[Tuple[str, int, int, int, int]]) -> dict:
    items = []
    for tag, i1, i2, j1, j2 in opcodes:
        source_block = sentences_1[i1:i2]
        target_block = sentences_2[j1:j2]
        items.append(
            {
                "tag": tag,
                "source_range": [i1, i2],
                "target_range": [j1, j2],
                "source_count": len(source_block),
                "target_count": len(target_block),
                "source_preview": source_block[:3],
                "target_preview": target_block[:3],
            }
        )
    return {
        "sentences_1_count": len(sentences_1),
        "sentences_2_count": len(sentences_2),
        "opcodes": items,
    }


def _llm_refine_verdict(
    ollama,
    pair: dict,
    semantic_threshold: float,
    llm_confidence_threshold: float,
) -> Tuple[str, float, str, str]:
    judge = _judge_pair_with_llm(ollama=ollama, source=pair["source"], target=pair["target"])
    verdict = judge["verdict"]
    confidence = float(judge["confidence"])
    reason = judge["reason"]
    cdelta = _critical_delta(pair["source"], pair["target"])

    if verdict == "equivalent" and confidence < llm_confidence_threshold:
        verdict = "changed_meaning"
        reason = "llm confidence below equivalent threshold"

    if cdelta["changed"]:
        verdict = "changed_meaning"
        reason = "critical legal terms changed"

    pair_sim = float(pair.get("similarity", 0.0))
    pair_lex = float(pair.get("lexical_similarity", 0.0))
    pair_tok = float(pair.get("token_overlap", 0.0))
    if (
        verdict == "changed_meaning"
        and not cdelta["changed"]
        and pair_sim >= max(semantic_threshold + 0.03, 0.91)
        and (pair_lex >= 0.95 or pair_tok >= 0.75)
        and confidence <= 0.82
    ):
        verdict = "equivalent"
        reason = "semantic+lexical guardrail overrides low-confidence strict LLM judgement"
        confidence = max(confidence, pair_sim)

    return verdict, confidence, reason, "llm"


def _analyze_replace_block(
    embedder,
    source_block: List[str],
    target_block: List[str],
    semantic_threshold: float,
    candidate_threshold: float,
    use_llm: bool,
    ollama=None,
    llm_confidence_threshold: float = 0.7,
) -> Tuple[List[dict], Dict[str, int], Dict[str, list]]:
    segments = []
    summary = _new_summary()
    stage_debug = {"embedding_pairs": [], "llm_judgements": []}

    if not source_block and not target_block:
        return segments, summary, stage_debug
    if not source_block:
        for sentence in target_block:
            _add_segment(
                segments,
                summary,
                {
                    "source": None,
                    "target": sentence,
                    "verdict": "added",
                    "confidence": 1.0,
                    "reason": "sentence inserted by difflib opcode",
                    "method": "difflib",
                    "similarity": 0.0,
                    "lexical_similarity": 0.0,
                    "token_overlap": 0.0,
                    "critical_delta": _blank_critical_delta(),
                },
            )
        return segments, summary, stage_debug
    if not target_block:
        for sentence in source_block:
            _add_segment(
                segments,
                summary,
                {
                    "source": sentence,
                    "target": None,
                    "verdict": "removed",
                    "confidence": 1.0,
                    "reason": "sentence removed by difflib opcode",
                    "method": "difflib",
                    "similarity": 0.0,
                    "lexical_similarity": 0.0,
                    "token_overlap": 0.0,
                    "critical_delta": _blank_critical_delta(),
                },
            )
        return segments, summary, stage_debug

    emb_1 = embedder.embed(source_block)
    emb_2 = embedder.embed(target_block)
    matrix = _build_similarity_matrix(emb_1, emb_2)
    pairs, used_i, used_j = align_sentence_pairs(
        source_block,
        target_block,
        matrix=matrix,
        candidate_threshold=candidate_threshold,
    )

    for pair in pairs:
        sem_verdict, sem_conf, sem_reason = _semantic_verdict(pair, semantic_threshold=semantic_threshold)
        stage_debug["embedding_pairs"].append(
            {
                "source": pair["source"],
                "target": pair["target"],
                "similarity": float(pair.get("similarity", 0.0)),
                "lexical_similarity": float(pair.get("lexical_similarity", 0.0)),
                "token_overlap": float(pair.get("token_overlap", 0.0)),
                "semantic_verdict": sem_verdict,
                "semantic_confidence": round(float(sem_conf), 4),
                "semantic_reason": sem_reason,
            }
        )
        verdict = sem_verdict
        confidence = sem_conf
        reason = sem_reason
        method = "semantic"
        if use_llm and ollama is not None:
            verdict, confidence, reason, method = _llm_refine_verdict(
                ollama=ollama,
                pair=pair,
                semantic_threshold=semantic_threshold,
                llm_confidence_threshold=llm_confidence_threshold,
            )
            stage_debug["llm_judgements"].append(
                {
                    "source": pair["source"],
                    "target": pair["target"],
                    "verdict": verdict,
                    "confidence": round(float(confidence), 4),
                    "reason": reason,
                }
            )
        _add_segment(
            segments,
            summary,
            {
                "source": pair["source"],
                "target": pair["target"],
                "verdict": verdict,
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "method": method,
                "similarity": float(pair.get("similarity", 0.0)),
                "lexical_similarity": float(pair.get("lexical_similarity", 0.0)),
                "token_overlap": float(pair.get("token_overlap", 0.0)),
                "critical_delta": _critical_delta(pair["source"], pair["target"]),
            },
        )

    for i, sentence in enumerate(source_block):
        if i not in used_i:
            _add_segment(
                segments,
                summary,
                {
                    "source": sentence,
                    "target": None,
                    "verdict": "removed",
                    "confidence": 1.0,
                    "reason": "no aligned sentence in target block",
                    "method": "difflib",
                    "similarity": 0.0,
                    "lexical_similarity": 0.0,
                    "token_overlap": 0.0,
                    "critical_delta": _blank_critical_delta(),
                },
            )

    for j, sentence in enumerate(target_block):
        if j not in used_j:
            _add_segment(
                segments,
                summary,
                {
                    "source": None,
                    "target": sentence,
                    "verdict": "added",
                    "confidence": 1.0,
                    "reason": "no aligned sentence in source block",
                    "method": "difflib",
                    "similarity": 0.0,
                    "lexical_similarity": 0.0,
                    "token_overlap": 0.0,
                    "critical_delta": _blank_critical_delta(),
                },
            )

    return segments, summary, stage_debug


def _finalize_result(segments: List[dict], summary: Dict[str, int], stage_outputs: Dict = None) -> Dict:
    meaning_preserved = summary["changed_meaning"] == 0 and summary["removed"] == 0 and summary["added"] == 0
    return {
        "meaning_preserved": meaning_preserved,
        "segments": segments,
        "segments_changed": [s for s in segments if s.get("verdict") in ["changed_meaning", "added", "removed"]],
        "summary": summary,
        "stage_outputs": stage_outputs or {},
    }


def run_difflib_semantic_compare(
    embedder,
    text_1: str,
    text_2: str,
    semantic_threshold: float,
    candidate_threshold: float,
    max_segments: int,
) -> Dict:
    s1 = split_sentences(text_1, max_segments=max_segments)
    s2 = split_sentences(text_2, max_segments=max_segments)
    if not s1 and not s2:
        return _finalize_result([], _new_summary(), stage_outputs={"difflib": {"sentences_1_count": 0, "sentences_2_count": 0, "opcodes": []}, "embedding": {"pairs_count": 0, "aligned_pairs": []}, "llm": {"enabled": False, "judgements_count": 0, "judgements": []}})

    matcher = SequenceMatcher(None, s1, s2)
    opcodes = matcher.get_opcodes()
    segments = []
    summary = _new_summary()
    embedding_pairs = []

    for tag, i1, i2, j1, j2 in opcodes:
        source_block = s1[i1:i2]
        target_block = s2[j1:j2]
        if tag == "equal":
            for source, target in zip(source_block, target_block):
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": source,
                        "target": target,
                        "verdict": "equivalent",
                        "confidence": 1.0,
                        "reason": "exact sentence match from difflib",
                        "method": "difflib",
                        "similarity": 1.0,
                        "lexical_similarity": 1.0,
                        "token_overlap": 1.0,
                        "critical_delta": _blank_critical_delta(),
                    },
                )
            continue

        block_segments, block_summary, block_debug = _analyze_replace_block(
            embedder=embedder,
            source_block=source_block,
            target_block=target_block,
            semantic_threshold=semantic_threshold,
            candidate_threshold=candidate_threshold,
            use_llm=False,
        )
        embedding_pairs.extend(block_debug["embedding_pairs"])
        for key in summary:
            summary[key] += block_summary[key]
        segments.extend(block_segments)

    stage_outputs = {
        "difflib": _build_difflib_stage_output(s1, s2, opcodes),
        "embedding": {
            "candidate_threshold": candidate_threshold,
            "pairs_count": len(embedding_pairs),
            "aligned_pairs": embedding_pairs,
        },
        "llm": {
            "enabled": False,
            "judgements_count": 0,
            "judgements": [],
        },
    }
    return _finalize_result(segments, summary, stage_outputs=stage_outputs)


def run_difflib_semantic_llm_compare(
    ollama,
    embedder,
    text_1: str,
    text_2: str,
    semantic_threshold: float,
    candidate_threshold: float,
    llm_confidence_threshold: float,
    max_segments: int,
) -> Dict:
    s1 = split_sentences(text_1, max_segments=max_segments)
    s2 = split_sentences(text_2, max_segments=max_segments)
    if not s1 and not s2:
        return _finalize_result([], _new_summary(), stage_outputs={"difflib": {"sentences_1_count": 0, "sentences_2_count": 0, "opcodes": []}, "embedding": {"pairs_count": 0, "aligned_pairs": []}, "llm": {"enabled": True, "judgements_count": 0, "judgements": []}})

    matcher = SequenceMatcher(None, s1, s2)
    opcodes = matcher.get_opcodes()
    segments = []
    summary = _new_summary()
    embedding_pairs = []
    llm_judgements = []

    for tag, i1, i2, j1, j2 in opcodes:
        source_block = s1[i1:i2]
        target_block = s2[j1:j2]
        if tag == "equal":
            for source, target in zip(source_block, target_block):
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": source,
                        "target": target,
                        "verdict": "equivalent",
                        "confidence": 1.0,
                        "reason": "exact sentence match from difflib",
                        "method": "difflib",
                        "similarity": 1.0,
                        "lexical_similarity": 1.0,
                        "token_overlap": 1.0,
                        "critical_delta": _blank_critical_delta(),
                    },
                )
            continue

        block_segments, block_summary, block_debug = _analyze_replace_block(
            embedder=embedder,
            source_block=source_block,
            target_block=target_block,
            semantic_threshold=semantic_threshold,
            candidate_threshold=candidate_threshold,
            use_llm=True,
            ollama=ollama,
            llm_confidence_threshold=llm_confidence_threshold,
        )
        embedding_pairs.extend(block_debug["embedding_pairs"])
        llm_judgements.extend(block_debug["llm_judgements"])
        for key in summary:
            summary[key] += block_summary[key]
        segments.extend(block_segments)

    stage_outputs = {
        "difflib": _build_difflib_stage_output(s1, s2, opcodes),
        "embedding": {
            "candidate_threshold": candidate_threshold,
            "pairs_count": len(embedding_pairs),
            "aligned_pairs": embedding_pairs,
        },
        "llm": {
            "enabled": True,
            "llm_confidence_threshold": llm_confidence_threshold,
            "judgements_count": len(llm_judgements),
            "judgements": llm_judgements,
        },
    }
    return _finalize_result(segments, summary, stage_outputs=stage_outputs)


def run_difflib_llm_compare(
    ollama,
    text_1: str,
    text_2: str,
    llm_confidence_threshold: float,
    max_segments: int,
) -> Dict:
    s1 = split_sentences(text_1, max_segments=max_segments)
    s2 = split_sentences(text_2, max_segments=max_segments)
    if not s1 and not s2:
        return _finalize_result(
            [],
            _new_summary(),
            stage_outputs={
                "difflib": {"sentences_1_count": 0, "sentences_2_count": 0, "opcodes": []},
                "embedding": {"enabled": False, "pairs_count": 0, "aligned_pairs": []},
                "llm": {"enabled": True, "llm_confidence_threshold": llm_confidence_threshold, "judgements_count": 0, "judgements": []},
            },
        )

    matcher = SequenceMatcher(None, s1, s2)
    opcodes = matcher.get_opcodes()
    segments = []
    summary = _new_summary()
    llm_judgements = []

    for tag, i1, i2, j1, j2 in opcodes:
        source_block = s1[i1:i2]
        target_block = s2[j1:j2]
        if tag == "equal":
            for source, target in zip(source_block, target_block):
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": source,
                        "target": target,
                        "verdict": "equivalent",
                        "confidence": 1.0,
                        "reason": "exact sentence match from difflib",
                        "method": "difflib",
                        "similarity": 1.0,
                        "lexical_similarity": 1.0,
                        "token_overlap": 1.0,
                        "critical_delta": _blank_critical_delta(),
                    },
                )
            continue

        max_len = max(len(source_block), len(target_block))
        for idx in range(max_len):
            source = source_block[idx] if idx < len(source_block) else None
            target = target_block[idx] if idx < len(target_block) else None
            if source and target:
                judge = _judge_pair_with_llm(ollama=ollama, source=source, target=target)
                raw_verdict = judge["verdict"]
                verdict = raw_verdict
                confidence = float(judge["confidence"])
                reason = judge["reason"]
                cdelta = _critical_delta(source, target)
                if verdict == "equivalent" and confidence < llm_confidence_threshold:
                    verdict = "changed_meaning"
                    reason = "llm confidence below equivalent threshold"
                if cdelta["changed"]:
                    verdict = "changed_meaning"
                    reason = "critical legal terms changed"

                llm_judgements.append(
                    {
                        "source": source,
                        "target": target,
                        "raw_verdict": raw_verdict,
                        "verdict": verdict,
                        "confidence": round(confidence, 4),
                        "reason": reason,
                    }
                )
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": source,
                        "target": target,
                        "verdict": verdict,
                        "confidence": round(confidence, 4),
                        "reason": reason,
                        "method": "llm_difflib",
                        "similarity": round(_lexical_ratio(source, target), 4),
                        "lexical_similarity": round(_lexical_ratio(source, target), 4),
                        "token_overlap": round(_token_overlap(source, target), 4),
                        "critical_delta": cdelta,
                    },
                )
            elif source and not target:
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": source,
                        "target": None,
                        "verdict": "removed",
                        "confidence": 1.0,
                        "reason": "sentence removed by difflib opcode",
                        "method": "difflib",
                        "similarity": 0.0,
                        "lexical_similarity": 0.0,
                        "token_overlap": 0.0,
                        "critical_delta": _blank_critical_delta(),
                    },
                )
            elif target and not source:
                _add_segment(
                    segments,
                    summary,
                    {
                        "source": None,
                        "target": target,
                        "verdict": "added",
                        "confidence": 1.0,
                        "reason": "sentence inserted by difflib opcode",
                        "method": "difflib",
                        "similarity": 0.0,
                        "lexical_similarity": 0.0,
                        "token_overlap": 0.0,
                        "critical_delta": _blank_critical_delta(),
                    },
                )

    stage_outputs = {
        "difflib": _build_difflib_stage_output(s1, s2, opcodes),
        "embedding": {
            "enabled": False,
            "pairs_count": 0,
            "aligned_pairs": [],
        },
        "llm": {
            "enabled": True,
            "llm_confidence_threshold": llm_confidence_threshold,
            "judgements_count": len(llm_judgements),
            "judgements": llm_judgements,
        },
    }
    return _finalize_result(segments, summary, stage_outputs=stage_outputs)


# Backward-compatible wrappers for previous test router usage.
def run_semantic_compare(
    embedder,
    text_1: str,
    text_2: str,
    semantic_threshold: float,
    candidate_threshold: float,
    max_segments: int,
) -> Dict:
    return run_difflib_semantic_compare(
        embedder=embedder,
        text_1=text_1,
        text_2=text_2,
        semantic_threshold=semantic_threshold,
        candidate_threshold=candidate_threshold,
        max_segments=max_segments,
    )


def run_llm_compare(
    ollama,
    embedder,
    text_1: str,
    text_2: str,
    llm_confidence_threshold: float,
    semantic_threshold: float,
    candidate_threshold: float,
    max_segments: int,
) -> Dict:
    return run_difflib_semantic_llm_compare(
        ollama=ollama,
        embedder=embedder,
        text_1=text_1,
        text_2=text_2,
        semantic_threshold=semantic_threshold,
        candidate_threshold=candidate_threshold,
        llm_confidence_threshold=llm_confidence_threshold,
        max_segments=max_segments,
    )
