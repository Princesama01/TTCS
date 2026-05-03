import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

from api.services.file_parser import parse_docx

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATASET_DIR = PROJECT_ROOT.parent / "evalution_dataset"
CASE_NAME_RE = re.compile(r"^data(\d+)$", re.IGNORECASE)
CHANGED_RE = re.compile(r"^(C\d+)_(BEFORE|AFTER)\s*:\s*(.+)$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def list_dataset_cases() -> List[Path]:
    if not DATASET_DIR.exists():
        return []
    pairs: List[Tuple[int, Path]] = []
    for case_dir in DATASET_DIR.iterdir():
        if not case_dir.is_dir():
            continue
        match = CASE_NAME_RE.match(case_dir.name)
        if not match:
            continue
        pairs.append((int(match.group(1)), case_dir))
    pairs.sort(key=lambda x: x[0])
    return [case_dir for _, case_dir in pairs]


def load_docx_text(path: Path) -> str:
    return parse_docx(path.read_bytes())


def parse_gt_file(path: Path) -> Dict:
    removed: List[str] = []
    added: List[str] = []
    changed_raw: Dict[str, Dict[str, str]] = {}
    section = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        title = line.rstrip(":").upper()
        if title in {"REMOVED", "ADDED", "CHANGED"}:
            section = title
            continue

        item = line[1:].strip() if line.startswith("-") else line
        if not item:
            continue

        if section == "REMOVED":
            _, _, content = item.partition(":")
            candidate = content.strip() if content else item
            if candidate:
                removed.append(normalize_text(candidate))
            continue

        if section == "ADDED":
            _, _, content = item.partition(":")
            candidate = content.strip() if content else item
            if candidate:
                added.append(normalize_text(candidate))
            continue

        if section == "CHANGED":
            match = CHANGED_RE.match(item)
            if not match:
                continue
            change_id, position, content = match.groups()
            change_id = change_id.upper()
            position = position.lower()
            changed_raw.setdefault(change_id, {})[position] = normalize_text(content)

    changed: List[Dict[str, str]] = []
    for change_id in sorted(changed_raw):
        pair = changed_raw[change_id]
        before = pair.get("before", "")
        after = pair.get("after", "")
        if not before and not after:
            continue
        changed.append({"id": change_id, "before": before, "after": after})

    return {
        "removed": sorted(set(removed)),
        "added": sorted(set(added)),
        "changed": changed,
    }


def parse_gt_json(path: Path) -> Dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    labels = payload.get("labels", {})

    removed: List[str] = []
    for item in labels.get("removed", []):
        if isinstance(item, dict):
            text = normalize_text(item.get("text", ""))
        else:
            text = normalize_text(str(item))
        if text:
            removed.append(text)

    added: List[str] = []
    for item in labels.get("added", []):
        if isinstance(item, dict):
            text = normalize_text(item.get("text", ""))
        else:
            text = normalize_text(str(item))
        if text:
            added.append(text)

    changed: List[Dict[str, str]] = []
    for idx, item in enumerate(labels.get("changed", []), start=1):
        if isinstance(item, dict):
            before = normalize_text(item.get("before", ""))
            after = normalize_text(item.get("after", ""))
            cid = str(item.get("id", f"C{idx}")).upper()
        else:
            before = ""
            after = ""
            cid = f"C{idx}"
        if before or after:
            changed.append({"id": cid, "before": before, "after": after})

    return {
        "removed": sorted(set(removed)),
        "added": sorted(set(added)),
        "changed": changed,
    }


def load_evalution_dataset() -> List[Dict]:
    cases: List[Dict] = []
    for case_dir in list_dataset_cases():
        before_path = case_dir / "before.docx"
        after_path = case_dir / "after.docx"
        gt_json_path = case_dir / "GT.json"
        gt_txt_path = case_dir / "GT.txt"
        if not (before_path.exists() and after_path.exists() and (gt_json_path.exists() or gt_txt_path.exists())):
            continue
        if gt_json_path.exists():
            gt = parse_gt_json(gt_json_path)
        else:
            gt = parse_gt_file(gt_txt_path)
        cases.append(
            {
                "case_id": case_dir.name,
                "before_text": load_docx_text(before_path),
                "after_text": load_docx_text(after_path),
                "ground_truth": gt,
            }
        )
    return cases
