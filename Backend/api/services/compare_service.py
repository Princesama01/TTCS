import difflib
from typing import List


class CompareService:
    @staticmethod
    def compare_texts(text1: str, text2: str) -> List[dict]:
        lines1 = text1.split("\n")
        lines2 = text2.split("\n")
        changes = []
        matcher = difflib.SequenceMatcher(None, lines1, lines2)

        line1_idx = 0
        line2_idx = 0
        for block in matcher.get_matching_blocks():
            i, j, size = block.a, block.b, block.size
            if i > line1_idx or j > line2_idx:
                removed_lines = lines1[line1_idx:i]
                added_lines = lines2[line2_idx:j]
                if removed_lines and added_lines:
                    changes.append(
                        {
                            "type": "modified",
                            "line_from": line1_idx + 1,
                            "line_to": i,
                            "v1_text": "\n".join(removed_lines),
                            "v2_text": "\n".join(added_lines),
                            "similarity": difflib.SequenceMatcher(None, " ".join(removed_lines), " ".join(added_lines)).ratio(),
                            "removed_lines_count": len(removed_lines),
                            "added_lines_count": len(added_lines),
                        }
                    )
                elif removed_lines:
                    changes.append(
                        {
                            "type": "removed",
                            "line_from": line1_idx + 1,
                            "line_to": i,
                            "v1_text": "\n".join(removed_lines),
                            "v2_text": None,
                            "removed_lines_count": len(removed_lines),
                        }
                    )
                elif added_lines:
                    changes.append(
                        {
                            "type": "added",
                            "line_from": j + 1,
                            "line_to": j + len(added_lines),
                            "v1_text": None,
                            "v2_text": "\n".join(added_lines),
                            "added_lines_count": len(added_lines),
                        }
                    )
            line1_idx = i + size
            line2_idx = j + size
        return changes

    @staticmethod
    def build_vector_context(points: list, limit_chars: int = 2500) -> str:
        snippets = []
        size = 0
        for point in points:
            payload = point.payload if hasattr(point, "payload") else point
            snippet = payload.get("content", "")
            if not snippet:
                continue
            header = f"[{payload.get('structure_path', '')}] "
            entry = header + snippet
            if size + len(entry) > limit_chars:
                break
            snippets.append(entry)
            size += len(entry)
        return "\n\n".join(snippets)

    @staticmethod
    def generate_ai_summary(ollama, doc1_name: str, doc2_name: str, changes: list, context1: str, context2: str, mode: str) -> str:
        if not changes:
            return "Hai tài liệu có nội dung tương tự nhau."
        prompt = (
            f"Bạn đang so sánh 2 tài liệu pháp lý:\n- Tài liệu 1: {doc1_name}\n- Tài liệu 2: {doc2_name}\n"
            f"Mode: {mode}\n\n"
            f"Số thay đổi phát hiện tự động: {len(changes)}\n\n"
            f"Ngữ cảnh vector từ tài liệu 1:\n{context1[:2000]}\n\n"
            f"Ngữ cảnh vector từ tài liệu 2:\n{context2[:2000]}\n\n"
            "Hãy tóm tắt điểm khác biệt quan trọng, rủi ro pháp lý có thể phát sinh, và đề xuất 3 mục cần review thủ công."
        )
        system = "Bạn là chuyên gia pháp lý, viết ngắn gọn, rõ ràng, không bịa thông tin."
        return ollama.generate(prompt=prompt, system=system, temperature=0.2)
