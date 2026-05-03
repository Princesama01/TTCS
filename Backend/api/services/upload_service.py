import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from api.services.file_parser import parse_file
from src.structure_parser import LegalStructureParser


class UploadTracker:
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            project_root = Path(__file__).parent.parent.parent
            storage_dir = project_root / "data" / "uploads"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cleanup_old_uploads()

    def _get_upload_file(self, upload_id: str) -> Path:
        return self.storage_dir / f"{upload_id}.json"

    def _cleanup_old_uploads(self, max_age_hours: int = 24):
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        for file_path in self.storage_dir.glob("*.json"):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                try:
                    file_path.unlink()
                except Exception:
                    pass

    def create_upload(self, upload_id: str, file_name: str, doc_id: str):
        with self._lock:
            upload_data = {
                "id": upload_id,
                "file_name": file_name,
                "doc_id": doc_id,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "pipeline_status": {
                    "parsing": "pending",
                    "chunking": "pending",
                    "embedding": "pending",
                    "indexing": "pending",
                },
                "progress": 0,
                "error": None,
            }
            self._get_upload_file(upload_id).write_text(json.dumps(upload_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_pipeline_step(self, upload_id: str, step: str, status: str, error: str = None):
        with self._lock:
            upload_file = self._get_upload_file(upload_id)
            if not upload_file.exists():
                return
            upload_data = json.loads(upload_file.read_text(encoding="utf-8"))
            upload_data["pipeline_status"][step] = status
            if error:
                upload_data["error"] = error
            values = list(upload_data["pipeline_status"].values())
            upload_data["progress"] = int((sum(1 for s in values if s == "completed") / len(values)) * 100)
            if upload_data["progress"] == 100:
                upload_data["completed_at"] = datetime.now().isoformat()
            upload_file.write_text(json.dumps(upload_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_upload_status(self, upload_id: str) -> Optional[dict]:
        with self._lock:
            upload_file = self._get_upload_file(upload_id)
            if not upload_file.exists():
                return None
            return json.loads(upload_file.read_text(encoding="utf-8"))


class UploadService:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline
        self.tracker = UploadTracker()

    def validate_file(self, filename: str, file_content: bytes) -> tuple[bool, Optional[str]]:
        filename_lower = filename.lower()
        if not any(filename_lower.endswith(ext) for ext in [".pdf", ".docx"]):
            return False, "Unsupported file type. Only .PDF and .DOCX files are allowed."
        if filename_lower.endswith(".pdf") and not file_content.startswith(b"%PDF"):
            return False, "Invalid PDF file: magic bytes mismatch"
        if filename_lower.endswith(".docx") and not file_content.startswith(b"PK"):
            return False, "Invalid DOCX file: magic bytes mismatch"
        max_file_size = 50 * 1024 * 1024
        if len(file_content) > max_file_size:
            return False, f"File too large. Max size: {max_file_size / (1024 * 1024)}MB"
        return True, None

    def save_original_file(self, doc_id: str, filename: str, file_content: bytes) -> dict:
        safe_name = self._sanitize_filename(filename)
        doc_dir = Path(__file__).parent.parent.parent / "data" / "documents" / doc_id / "original"
        doc_dir.mkdir(parents=True, exist_ok=True)
        file_path = doc_dir / safe_name
        file_path.write_bytes(file_content)
        rel_path = file_path.relative_to(Path(__file__).parent.parent.parent / "data" / "documents").as_posix()
        return {
            "original_file_name": safe_name,
            "original_file_rel_path": rel_path,
            "original_file_content_type": self._guess_content_type(safe_name),
        }

    async def process_upload(self, upload_id: str, doc_id: str, file_content: bytes, filename: str):
        self.tracker.create_upload(upload_id, filename, doc_id)
        self.tracker.update_pipeline_step(upload_id, "parsing", "processing")
        text, _file_type = parse_file(file_content, filename)
        if not text or len(text.strip()) < 10:
            self.tracker.update_pipeline_step(upload_id, "parsing", "error", "File appears empty")
            raise ValueError("File appears to be empty or too short")

        self._save_document_content(doc_id, text)
        structure_data = self._parse_document_structure(text)
        self._save_document_structure(doc_id, structure_data)
        self.tracker.update_pipeline_step(upload_id, "parsing", "completed")

        self.tracker.update_pipeline_step(upload_id, "chunking", "processing")
        stats = self.pipeline.index_document(text=text, doc_id=doc_id, version="v1") if self.pipeline else {"total": 0}
        self.tracker.update_pipeline_step(upload_id, "chunking", "completed")
        self.tracker.update_pipeline_step(upload_id, "embedding", "completed")
        self.tracker.update_pipeline_step(upload_id, "indexing", "completed")
        return {"success": True, "chunk_count": stats.get("total", 0), "stats": stats}

    def get_upload_status(self, upload_id: str) -> Optional[dict]:
        return self.tracker.get_upload_status(upload_id)

    def _save_document_content(self, doc_id: str, content: str):
        doc_dir = Path(__file__).parent.parent.parent / "data" / "documents" / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        payload = {"doc_id": doc_id, "content": content, "saved_at": datetime.now().isoformat(), "length": len(content)}
        (doc_dir / "content.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _parse_document_structure(self, text: str) -> dict:
        parser = LegalStructureParser()
        articles = parser.parse(text)

        def node_to_dict(node):
            return {
                "level": node.level,
                "number": node.number,
                "title": node.title[:100],
                "content": node.content[:500] if node.content else "",
                "article_no": node.article_no,
                "clause_no": node.clause_no,
                "point_no": node.point_no,
                "structure_path": node.structure_path,
                "char_start": node.char_start,
                "char_end": node.char_end,
                "children": [node_to_dict(child) for child in node.children],
            }

        return {
            "success": True,
            "articles": [node_to_dict(art) for art in articles],
            "total_articles": len(articles),
            "parsed_at": datetime.now().isoformat(),
        }

    def _save_document_structure(self, doc_id: str, structure_data: dict):
        doc_dir = Path(__file__).parent.parent.parent / "data" / "documents" / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        (doc_dir / "structure.json").write_text(json.dumps(structure_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_document_content(self, doc_id: str) -> Optional[dict]:
        content_file = Path(__file__).parent.parent.parent / "data" / "documents" / doc_id / "content.json"
        if not content_file.exists():
            return None
        return json.loads(content_file.read_text(encoding="utf-8"))

    def get_document_structure(self, doc_id: str) -> Optional[dict]:
        structure_file = Path(__file__).parent.parent.parent / "data" / "documents" / doc_id / "structure.json"
        if not structure_file.exists():
            return None
        return json.loads(structure_file.read_text(encoding="utf-8"))

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        name = Path(filename or "").name.strip()
        if not name:
            name = "uploaded_file"
        name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
        return name[:180]

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        lowered = filename.lower()
        if lowered.endswith(".pdf"):
            return "application/pdf"
        if lowered.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/octet-stream"
