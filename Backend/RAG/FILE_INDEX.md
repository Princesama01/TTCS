# 🤖 RAG Document Q&A System - File Index

## 📋 Quick Navigation

### 🎯 Start Here
1. [PROJECT_COMPLETE.md](PROJECT_COMPLETE.md) - **Read this first!** Project summary and achievements
2. [QUICKSTART.md](QUICKSTART.md) - 5-minute setup guide
3. [README.md](README.md) - Complete documentation (Vietnamese)

### 📚 Documentation
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Architecture and component details
- [LICENSE](LICENSE) - MIT License
- API Documentation - Auto-generated at `/api/docs` when server runs

---

## 📁 Complete File Reference

### 🔧 Configuration (5 files)
| File | Purpose | When to Edit |
|------|---------|--------------|
| `config.py` | Global settings & paths | Change model paths, chunk size |
| `.env.example` | Environment template | Copy to `.env` for configuration |
| `.env` | **User config** (create from example) | Set your specific values |
| `requirements.txt` | Python dependencies | Add new packages |
| `.gitignore` | Git exclusions | Exclude additional files |

### 🧠 Core System (8 files in `src/`)
| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `src/__init__.py` | 15 | Package initialization | Module exports |
| `src/document_processor.py` | 250 | PDF text extraction & chunking | `PDFProcessor`, `optimize_chunk_size()` |
| `src/embeddings.py` | 120 | BGE embedding generation | `EmbeddingGenerator`, `LangChainEmbeddings` |
| `src/vector_store.py` | 280 | FAISS vector database | `VectorStore`, `create_optimized_index()` |
| `src/retriever.py` | 320 | Multi-query + reranking | `AdvancedRetriever`, `MultiQueryRetriever`, `CrossEncoderReranker` |
| `src/llm.py` | 200 | Llama 3 LLM integration | `LlamaLLM`, `create_rag_prompt()` |
| `src/rag_pipeline.py` | 280 | Main RAG orchestration | `RAGPipeline` |
| `src/evaluation.py` | 250 | RAGAS evaluation | `RAGEvaluator` |

### 🌐 API Server (4 files in `api/`)
| File | Lines | Purpose | Endpoints |
|------|-------|---------|-----------|
| `api/__init__.py` | 5 | Package init | - |
| `api/main.py` | 120 | FastAPI application | Server setup |
| `api/routes.py` | 200 | API endpoints | `/chat`, `/upload`, `/sources`, `/statistics` |
| `api/models.py` | 80 | Pydantic models | Request/response schemas |

### 🛠️ Utilities (3 files in `utils/`)
| File | Lines | Purpose |
|------|-------|---------|
| `utils/__init__.py` | 5 | Package init |
| `utils/logger.py` | 60 | Logging configuration (loguru) |
| `utils/performance.py` | 120 | Performance monitoring |

### 📜 Scripts (4 files in `scripts/`)
| File | Lines | Purpose | Usage |
|------|-------|---------|-------|
| `scripts/__init__.py` | 5 | Package init | - |
| `scripts/download_models.py` | 120 | Download Llama 3 model | `python scripts/download_models.py` |
| `scripts/ingest_documents.py` | 80 | Document ingestion | `python scripts/ingest_documents.py` |
| `scripts/evaluate_system.py` | 100 | Run RAGAS evaluation | `python scripts/evaluate_system.py --use-sample` |

### 🎨 Web Interface (1 file in `web/`)
| File | Lines | Purpose |
|------|-------|---------|
| `web/index.html` | 300 | Chat UI with real-time updates |

### 🎬 Demo & Verification (3 files)
| File | Lines | Purpose | Usage |
|------|-------|---------|-------|
| `demo.py` | 250 | Feature demonstrations | `python demo.py` |
| `verify_setup.py` | 200 | System verification | `python verify_setup.py` |

### 📊 Data & Directories
| Directory | Purpose | Auto-created |
|-----------|---------|--------------|
| `data/documents/` | Input PDF files | ✅ |
| `data/processed/` | Processed chunks | ✅ |
| `data/vector_store/` | FAISS index | ✅ |
| `data/evaluation/` | Test datasets | ✅ |
| `models/` | Model files (.gguf) | ✅ |
| `logs/` | Application logs | ✅ |

---

## 🎯 File Usage by Task

### Task 1: Initial Setup
```
1. Read: QUICKSTART.md
2. Edit: .env (copy from .env.example)
3. Run: verify_setup.py
4. Run: scripts/download_models.py
```

### Task 2: Add Documents
```
1. Add PDFs to: data/documents/
2. Run: scripts/ingest_documents.py
3. Check: logs/rag_system.log
```

### Task 3: Start System
```
1. Run: python api/main.py
2. Open: http://localhost:8000
3. Test: web/index.html (served automatically)
```

### Task 4: Customize System
```
1. Modify prompts: src/llm.py (create_rag_prompt)
2. Adjust chunks: config.py (CHUNK_SIZE)
3. Tune retrieval: config.py (TOP_K_RETRIEVAL)
4. Change models: config.py (MODEL_PATHS)
```

### Task 5: Evaluate
```
1. Prepare dataset: data/evaluation/test_questions.json
2. Run: scripts/evaluate_system.py
3. Check results: evaluation_results/
```

---

## 📈 Component Dependencies

```
config.py
    ↓
[All modules depend on config]
    ↓
src/document_processor.py → src/embeddings.py
    ↓                              ↓
src/vector_store.py ← ← ← ← ← ← ← ←
    ↓
src/retriever.py → src/llm.py
    ↓                    ↓
    └─→ src/rag_pipeline.py ←─┘
              ↓
         api/routes.py
              ↓
         api/main.py
              ↓
         web/index.html
```

---

## 🔍 Find What You Need

### "How do I...?"

**Change the LLM model?**
- Edit: `config.py` → `LLAMA_MODEL_PATH`
- Update: `src/llm.py` if using different model format

**Modify chunk size?**
- Edit: `config.py` → `CHUNK_SIZE` and `CHUNK_OVERLAP`
- Re-run: `scripts/ingest_documents.py --recreate`

**Add a new API endpoint?**
- Edit: `api/routes.py` - Add route function
- Update: `api/models.py` - Add Pydantic model if needed

**Customize the chat interface?**
- Edit: `web/index.html` - HTML/CSS/JavaScript

**Change prompts?**
- Edit: `src/llm.py` → `create_rag_prompt()` or `create_conversation_prompt()`

**Add more evaluation metrics?**
- Edit: `src/evaluation.py` → Add RAGAS metrics

**Change logging behavior?**
- Edit: `utils/logger.py` → Modify loguru configuration

---

## 📊 File Statistics

| Category | Files | Total Lines |
|----------|-------|-------------|
| Core System | 8 | ~1,900 |
| API | 4 | ~400 |
| Scripts | 4 | ~300 |
| Utils | 3 | ~185 |
| Web UI | 1 | ~300 |
| Config | 5 | ~200 |
| Documentation | 7 | ~2,000 |
| **Total** | **32** | **~5,285** |

---

## 🎨 Code Quality Features

✅ **Type Hints**: All functions have type annotations  
✅ **Docstrings**: Comprehensive documentation  
✅ **Error Handling**: Try-except with logging  
✅ **Logging**: Structured with loguru  
✅ **Configuration**: Centralized in config.py  
✅ **Modularity**: Clear separation of concerns  
✅ **Scalability**: Production-ready architecture  

---

## 🚀 Quick Commands Reference

```bash
# Verification
python verify_setup.py

# Model Download
python scripts/download_models.py

# Document Ingestion
python scripts/ingest_documents.py
python scripts/ingest_documents.py --recreate  # Force rebuild

# Server
python api/main.py

# Demo
python demo.py

# Evaluation
python scripts/evaluate_system.py --use-sample
python scripts/evaluate_system.py --dataset path/to/test.json

# Python SDK
python -c "from src.rag_pipeline import RAGPipeline; print('OK')"
```

---

## 📖 Learning Path

**Beginner**:
1. Start with `QUICKSTART.md`
2. Run `verify_setup.py`
3. Try `demo.py`
4. Explore `web/index.html`

**Intermediate**:
1. Read `PROJECT_STRUCTURE.md`
2. Review `src/rag_pipeline.py`
3. Customize `config.py`
4. Modify prompts in `src/llm.py`

**Advanced**:
1. Study `src/retriever.py` (reranking)
2. Optimize `src/vector_store.py`
3. Extend `api/routes.py`
4. Implement custom evaluation in `src/evaluation.py`

---

## 🎯 Priority Files to Understand

**Must Read** (Core Logic):
1. `src/rag_pipeline.py` - Main orchestration
2. `src/retriever.py` - Advanced retrieval
3. `src/llm.py` - Prompt engineering
4. `config.py` - Configuration

**Important** (Integration):
5. `api/main.py` - API setup
6. `api/routes.py` - Endpoints
7. `scripts/ingest_documents.py` - Data ingestion

**Supporting** (Enhancement):
8. `src/evaluation.py` - Quality metrics
9. `utils/performance.py` - Monitoring
10. `demo.py` - Usage examples

---

**Total Project**: 32 files, ~5,285 lines, Production-ready ✅

**Next Step**: Open `PROJECT_COMPLETE.md` for full project summary!
