import json
import re
from typing import Optional

import requests

# Prompt templates lấy từ TTCS.1/backend/api/ollama_client.py
_BASE_LEGAL_SYSTEM = """Bạn là công cụ phân tích văn bản pháp lý tự động.

QUY TẮC BẮT BUỘC — KHÔNG ĐƯỢC VI PHẠM:
1. CHỈ sử dụng thông tin có trong [CONTEXT] được cung cấp. TUYỆT ĐỐI không thêm thông tin từ kiến thức bên ngoài.
2. Mọi nhận định PHẢI kèm trích dẫn nguồn dạng [Điều X/X.Y] hoặc [structure_path].
3. Nếu context không đủ thông tin để trả lời → trả về: {"status": "insufficient_context", "reason": "<lý do cụ thể>"}
4. KHÔNG đưa ra kết luận pháp lý, không tư vấn, không đánh giá tính hợp pháp.
5. KHÔNG suy diễn ý nghĩa ngoài văn bản gốc."""

_QA_SYSTEM = _BASE_LEGAL_SYSTEM + """

NHIỆM VỤ: Trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.
OUTPUT FORMAT — phải trả về JSON hợp lệ:
{
  "answer": "<câu trả lời ngắn gọn, CHỈ từ thông tin trong context>",
  "citations": [
    {
      "structure_path": "<đường dẫn chính xác từ [CITATION] block>",
      "excerpt": "<trích dẫn trực tiếp từ văn bản, tối đa 150 ký tự>",
      "version": "v1|v2"
    }
  ],
  "confidence": "high|medium|low",
  "confidence_reason": "<lý do đánh giá độ tin cậy>",
  "disclaimer": "Kết quả phân tích tự động, không phải tư vấn pháp lý."
}"""


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5"):
        self.base_url = base_url
        self.model_name = model_name
        self.generate_url = f"{base_url}/api/generate"
        self._resolved_model_name = None

    def _get_available_models(self) -> list:
        response = requests.get(f"{self.base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            return []
        models = response.json().get("models", [])
        return [m.get("name", "") for m in models if m.get("name")]

    def _resolve_model_name(self) -> str:
        if self._resolved_model_name:
            return self._resolved_model_name
        available = self._get_available_models()
        if not available:
            self._resolved_model_name = self.model_name
            return self._resolved_model_name

        if self.model_name in available:
            self._resolved_model_name = self.model_name
            return self._resolved_model_name

        pref = self.model_name.lower()
        for name in available:
            if name.lower().startswith(pref):
                self._resolved_model_name = name
                return self._resolved_model_name

        for name in available:
            if pref in name.lower():
                self._resolved_model_name = name
                return self._resolved_model_name

        if "qwen2.5" in pref:
            for name in available:
                if "qwen2.5" in name.lower():
                    self._resolved_model_name = name
                    return self._resolved_model_name

        self._resolved_model_name = self.model_name
        return self._resolved_model_name

    def health_check(self) -> dict:
        try:
            model_names = self._get_available_models()
            resolved = self._resolve_model_name()
            has_model = resolved in model_names
            if model_names:
                return {
                    "status": "success" if has_model else "running",
                    "requested_model": self.model_name,
                    "resolved_model": resolved,
                    "available_models": model_names,
                }
            return {"status": "error"}
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.4) -> str:
        model = self._resolve_model_name()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        try:
            response = requests.post(self.generate_url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "")
            if response.status_code == 404 and "model" in response.text.lower():
                return (
                    f"Error: model '{model}' not found on Ollama. "
                    f"Run: ollama pull {self.model_name}"
                )
            return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"

    @staticmethod
    def extract_paths_from_context(context: str) -> list:
        paths = set()
        for line in context.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and "]" in line:
                paths.add(line[1: line.find("]")].strip())
            if "structure_path:" in line:
                paths.add(line.split("structure_path:", 1)[1].strip())
        return [p for p in paths if p]

    @staticmethod
    def _extract_json_object(raw: str) -> Optional[str]:
        if not raw:
            return None
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
        if fence_match:
            raw = fence_match.group(1).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return raw[start : end + 1]

    @classmethod
    def _parse_json_response(cls, raw: str) -> dict:
        json_block = cls._extract_json_object(raw)
        if not json_block:
            return {}
        try:
            parsed = json.loads(json_block)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _validate_citations(result: dict, valid_paths: list) -> dict:
        citations = result.get("citations", [])
        if not isinstance(citations, list):
            result["citations"] = []
            return result
        if not valid_paths:
            result["citations"] = citations
            return result

        path_set = set(valid_paths)
        validated = []
        for item in citations:
            if not isinstance(item, dict):
                continue
            path = str(item.get("structure_path", "")).strip()
            excerpt = str(item.get("excerpt", "")).strip()
            if path and path in path_set:
                validated.append({"structure_path": path, "excerpt": excerpt})
        result["citations"] = validated
        return result

    def ask_question_with_citations(self, question: str, context: str, valid_paths: Optional[list] = None) -> dict:
        context = (context or "").strip()
        if not context:
            return {
                "status": "insufficient_context",
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này.",
                "citations": [],
                "confidence": "low",
                "confidence_reason": "Không có context từ vector store.",
            }

        context_paths = valid_paths if valid_paths is not None else self.extract_paths_from_context(context)
        prompt = (
            f"""[CONTEXT]
{context}
[/CONTEXT]

[CÂU HỎI]
{question}
[/CÂU HỎI]

TRƯỚC KHI TRẢ LỜI — hãy thực hiện theo thứ tự:
Bước 1: Tìm trong [CONTEXT] những đoạn liên quan trực tiếp đến câu hỏi.
Bước 2: Xác định structure_path của từng đoạn liên quan.
Bước 3: Nếu KHÔNG tìm thấy thông tin liên quan → trả về confidence="low", answer="Không có thông tin trong tài liệu".
Bước 4: Nếu CÓ → tổng hợp câu trả lời CHỈ từ những đoạn đã tìm, trích dẫn nguồn.

Trả về JSON theo format trong system prompt."""
        )
        raw = self.generate(prompt=prompt, system=_QA_SYSTEM, temperature=0.1)
        parsed = self._parse_json_response(raw)

        if not parsed:
            parsed = {
                "status": "insufficient_context",
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này.",
                "citations": [],
                "confidence": "low",
                "confidence_reason": "Không parse được output JSON từ mô hình.",
            }

        parsed = self._validate_citations(parsed, context_paths)
        answer = str(parsed.get("answer", "")).strip()
        citations = parsed.get("citations", [])
        if not isinstance(citations, list):
            citations = []

        status = "ok"
        if not citations:
            status = "insufficient_context"
            if not answer:
                answer = "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này."
        if not answer:
            answer = "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này."
            status = "insufficient_context"

        confidence = str(parsed.get("confidence", "low")).strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"

        confidence_reason = str(parsed.get("confidence_reason", "")).strip()
        if not confidence_reason:
            confidence_reason = (
                "Có trích dẫn hợp lệ từ context." if status == "ok" else "Thiếu bằng chứng rõ ràng trong context."
            )

        return {
            "status": status,
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "confidence_reason": confidence_reason,
        }

    def ask_question(self, question: str, context: str) -> str:
        result = self.ask_question_with_citations(question=question, context=context)
        return result.get("answer", "Không có đủ dữ liệu để kết luận.")
