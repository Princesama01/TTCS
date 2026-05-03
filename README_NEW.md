# TTCS Stack (Backend + Frontend)

## Những gì đã refactor

### 1. Frontend trong `Frontend/`
- Đồng bộ UI/UX bằng style chung: `Frontend/styles/main.css`.
- Màn hình chính:
  - `index.html` (dashboard + health + stats)
  - `upload.html` (upload + pipeline tracking)
  - `documents.html` (list/clauses/delete + mở file gốc)
  - `search.html` (semantic search)
  - `compare.html` (compare 2 docs + tuning params + detail)
  - `chat.html` (Q&A + citations)
  - `stats.html` (system stats + endpoint checks)

### 2. API đang dùng bởi Frontend
- `GET /`, `GET /health`, `GET /api/health`
- `GET /api/stats`
- `GET /api/documents`
- `GET /api/documents/{doc_id}/clauses`
- `GET /api/documents/{doc_id}/file`
- `GET /api/documents/{doc_id}/file/content`
- `DELETE /api/documents/{doc_id}`
- `POST /api/upload`
- `GET /api/upload/status/{upload_id}`
- `POST /api/search`
- `POST /api/ask`
- `POST /api/compare-documents`
- `GET /api/evaluation/chunking`
- `GET /api/evaluation/chunking/report`
- `POST /api/evaluation/chunking/run`

### 3. Lưu file gốc khi upload
- Khi upload `.docx` hoặc `.pdf`, backend vẫn parse/index như cũ.
- Đồng thời lưu file gốc tại:
  - `Backend/data/documents/<doc_id>/original/<filename>`
- Metadata tài liệu lưu thêm:
  - `has_original_file`
  - `original_file_name`
  - `original_file_rel_path`
  - `original_file_content_type`

## Chạy nhanh

### Cách 1: chạy cả 2 cùng lúc
```bat
start_new.bat
```

### Cách 2: chạy backend riêng
```bat
start_backend_new.bat
```

### Cách 3: chạy thủ công
Terminal 1:
```bat
.venv\Scripts\activate
uvicorn api.main:app --app-dir "Backend" --host 0.0.0.0 --port 5000 --reload
```

Terminal 2:
```bat
python -m http.server 8000 --directory "Frontend"
```

## Truy cập
- Frontend: http://localhost:8000
- Backend: http://localhost:5000
- API docs: http://localhost:5000/docs

## Ollama model
- Mặc định backend dùng `qwen2.5-3B`.
- Có thể override:
```bat
set OLLAMA_MODEL=qwen2.5-3B
set OLLAMA_BASE_URL=http://localhost:11434
```
- Nếu model chưa có:
```bat
ollama pull qwen2.5
```

## Cải tiến đã tích hợp (Chunking / Retrieval / Anti-hallucination)

### 1) Chunking & Data Pipeline
- Bổ sung bộ chiến lược chunking trong `Backend/src/chunking_strategies.py`:
  - `structural`
  - `recursive`
  - `hybrid`
- Mặc định cấu hình chunk hiện tại theo kết quả tối ưu:
  - `MICRO=256`, `MACRO=512`, `XREF=1024`, overlap `0`.
- Pipeline có thể chọn strategy bằng biến môi trường:
```bat
set CHUNKING_STRATEGY=recursive
```

### 2) Retrieval nâng cao
- `POST /api/search` và `POST /api/ask` hỗ trợ:
  - Hybrid search (`vector + keyword rerank`)
  - Filter theo `article_no`, `clause_no`, `version`, `doc_id`
  - Điều chỉnh `top_k`, `rerank_alpha`, `candidate_multiplier`
- `search_mode`:
  - `vector`: chỉ vector retrieval
  - `hybrid`: vector retrieval + keyword reranking

### 3) Prompt guardrails & giảm hallucination
- Tầng hỏi đáp (`/api/ask`) đã thêm:
  - Hard-stop khi không đủ context
  - Structured output: `status`, `confidence`, `confidence_reason`
  - Citation validation theo `structure_path` có trong context truy xuất
- Nguyên tắc áp dụng:
  - Không đủ bằng chứng → trả `Không có đủ dữ liệu để kết luận.`

### 4) Đánh giá chunking
- Chạy benchmark chunking:
```bat
POST /api/evaluation/chunking/run
```
- Kết quả JSON:
  - `Backend/evaluation/results/chunking_experiment_results.json`
- Báo cáo Markdown:
  - `Backend/evaluation/results/chunking_report.md`

## Xây dựng Dataset & Đánh giá Baseline (đã căn chỉnh theo hệ thống hiện tại)

### 👤 Người 1 – Xây dựng tập dữ liệu (Dataset Construction)
**Mục tiêu**
- Tạo bộ dữ liệu chuẩn để đánh giá bài toán so sánh thay đổi văn bản pháp lý.

**Công việc**
1. Thu thập dữ liệu
   - Nguồn: hợp đồng mẫu, phụ lục, văn bản pháp lý.
   - Mỗi case cần có 2 phiên bản: `before` và `after`.
   - Bắt buộc có thay đổi thực tế: sửa số, thêm/xóa điều khoản, sửa nội dung.
2. Chuẩn hóa dữ liệu
   - Định dạng đầu vào hiện tại của hệ thống: `.docx`.
   - Cấu trúc thư mục:
     - `evalution_dataset/dataN/before.docx`
     - `evalution_dataset/dataN/after.docx`
     - `evalution_dataset/dataN/GT.json`
   - Nội dung phải UTF-8, sạch nhiễu (khoảng trắng, dòng rác).
3. Gán nhãn ground truth
   - `GT.json` theo schema thống nhất:
     - `labels.removed[]` (id + text)
     - `labels.added[]` (id + text)
     - `labels.changed[]` (id + before + after)
4. Phân loại dữ liệu
   - Gắn thêm mức thay đổi theo case: `micro`, `macro`, `cross-reference` (có thể lưu phụ trong metadata).

**Output**
- Bộ dataset hoàn chỉnh trong `evalution_dataset/`.
- Ground truth chuẩn theo format parser hiện tại (`GT.json`).
- Danh sách tài liệu nguồn (khuyến nghị lưu thêm file `sources.json`).

### 👤 Người 2 – Xây dựng Baseline System
**Mục tiêu**
- Tạo baseline không dùng mô hình ngữ nghĩa sâu để so sánh với hệ RAG.

**Công việc**
1. Baseline đơn giản
   - Keyword matching
   - TF-IDF cosine
   - Rule-based diff (đang có trong `Backend/evaluation/baseline.py`)
2. Ví dụ baseline hiện có
   - So sánh trực tiếp theo dòng văn bản.
   - Ghép cặp thay đổi bằng chuỗi tương đồng (`difflib`).
3. Hạn chế baseline
   - Không hiểu ngữ nghĩa sâu/paraphrase.
   - Dễ sai khi câu dài hoặc đảo cấu trúc.
   - Kém ở thay đổi liên kết chéo.

**Output**
- Code baseline.
- File kết quả baseline trên toàn bộ dataset (trong `Backend/evaluation/results/evaluation_results.json`).
- Có thể chọn baseline khi chạy eval qua biến môi trường:
  - `EVAL_BASELINE_METHOD=rule_based_diff` (mặc định)
  - `EVAL_BASELINE_METHOD=keyword`
  - `EVAL_BASELINE_METHOD=tfidf`

### 👤 Người 3 – Đánh giá hệ thống (Evaluation)
**Mục tiêu**
- Đánh giá RAG so với baseline trên cùng dataset.

**Công việc**
1. Metric chính cho dataset hiện tại (diff-based)
   - Precision / Recall / F1 cho từng loại:
     - `removed`
     - `added`
     - `changed`
   - Overall Precision / Recall / F1 (micro-average).
2. Retrieval metric (Top-k, MRR)
   - Chỉ dùng khi có retrieval ground truth riêng (query -> relevant article/chunk).
   - Với dataset hiện tại chỉ có before/after + diff GT, retrieval metric để `N/A`.
3. So sánh baseline vs RAG
   - Xuất bảng:
     - Baseline vs RAG theo các metric ở trên.
   - Bổ sung nhận xét định tính theo từng nhóm lỗi.
   - Workflow RAG trong eval hiện tại: `difflib + semantic (embedding) + llm judge`.

**Output**
- Bảng kết quả đánh giá từ endpoint `/api/evaluation`.
- JSON kết quả: `Backend/evaluation/results/evaluation_results.json`.
- Biểu đồ (nếu cần) dựng từ dữ liệu `per_case`.
