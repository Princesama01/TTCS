import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class DocumentService:
    def __init__(self, base_path: str = None):
        if base_path is None:
            project_root = Path(__file__).parent.parent.parent.resolve()
            base_path = str(project_root / "data" / "documents")
        self.base_path = os.path.abspath(base_path)
        self.meta_path = os.path.join(self.base_path, "metadata.json")
        os.makedirs(self.base_path, exist_ok=True)
        self._ensure_metadata()

    def _validate_path(self, file_path: str) -> str:
        abs_path = os.path.abspath(os.path.join(self.base_path, file_path))
        if not abs_path.startswith(self.base_path):
            raise ValueError("Invalid path: directory traversal attempt detected")
        return abs_path

    def _ensure_metadata(self):
        if not os.path.exists(self.meta_path):
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_metadata(self) -> dict:
        with open(self.meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_metadata(self, data: dict):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_document(self, doc_id: str, name: str, file_type: str, size: int, version: str = "v1") -> dict:
        metadata = self._load_metadata()
        metadata[doc_id] = {
            "id": doc_id,
            "name": name,
            "file_type": file_type,
            "size": size,
            "created_at": datetime.now().isoformat(),
            "status": "processing",
            "chunk_count": 0,
            "version": version,
            "has_original_file": False,
            "original_file_name": None,
            "original_file_rel_path": None,
            "original_file_content_type": None,
        }
        self._save_metadata(metadata)
        return metadata[doc_id]

    def update_document_file_info(
        self,
        doc_id: str,
        *,
        original_file_name: str,
        original_file_rel_path: str,
        original_file_content_type: str,
    ) -> dict:
        metadata = self._load_metadata()
        if doc_id not in metadata:
            raise KeyError(f"Document {doc_id} not found")
        metadata[doc_id]["has_original_file"] = True
        metadata[doc_id]["original_file_name"] = original_file_name
        metadata[doc_id]["original_file_rel_path"] = original_file_rel_path
        metadata[doc_id]["original_file_content_type"] = original_file_content_type
        self._save_metadata(metadata)
        return metadata[doc_id]

    def update_document_status(self, doc_id: str, status: str, chunk_count: Optional[int] = None) -> dict:
        metadata = self._load_metadata()
        if doc_id not in metadata:
            raise KeyError(f"Document {doc_id} not found")
        metadata[doc_id]["status"] = status
        if chunk_count is not None:
            metadata[doc_id]["chunk_count"] = chunk_count
        self._save_metadata(metadata)
        return metadata[doc_id]

    def get_document(self, doc_id: str) -> dict:
        metadata = self._load_metadata()
        if doc_id not in metadata:
            raise KeyError(f"Document {doc_id} not found")
        return metadata[doc_id]

    def get_all_documents(self) -> List[dict]:
        return list(self._load_metadata().values())

    def get_original_file_info(self, doc_id: str) -> dict:
        doc = self.get_document(doc_id)
        rel_path = doc.get("original_file_rel_path")
        if not doc.get("has_original_file") or not rel_path:
            raise FileNotFoundError(f"No original file found for {doc_id}")

        abs_path = self._validate_path(rel_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Original file path missing for {doc_id}")

        return {
            "name": doc.get("original_file_name") or os.path.basename(abs_path),
            "content_type": doc.get("original_file_content_type") or "application/octet-stream",
            "relative_path": rel_path,
            "absolute_path": abs_path,
            "size": os.path.getsize(abs_path),
        }

    def delete_document(self, doc_id: str):
        metadata = self._load_metadata()
        if doc_id in metadata:
            del metadata[doc_id]
            self._save_metadata(metadata)
        doc_path = self._validate_path(doc_id)
        if os.path.exists(doc_path):
            shutil.rmtree(doc_path)
