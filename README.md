# 🛡️ Secure RAG MVP

> A defense-in-depth, fully local Retrieval-Augmented Generation system with trusted/quarantine document separation, output firewall, and built-in red-team evaluation.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-orange.svg)](https://ollama.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

---

## 🏗️ Architecture Overview

```
User Question → API → Retrieval (trusted only) → Prompt Builder → Ollama LLM → Output Firewall → Response + Citations
                 ↑
Document Upload → Loader → Normalizer → Security Scanner → Chunker → Embeddings → Trusted/Quarantine Store
```

### Key Security Layers

| Layer | Purpose | Defense |
|-------|---------|---------|
| **Input Scanner** | Detect prompt injection in documents | Regex patterns, URL allowlist, trust scoring |
| **Trusted/Quarantine** | Isolate suspicious documents | Separate ChromaDB collections |
| **Hardened Prompts** | Resist injection at generation | Strict Jinja2 templates, context-as-data framing |
| **Output Firewall** | Catch what got through | URL sanitization, leak detection, groundedness check |
| **Policy Engine** | Centralized decisions | ALLOW / WARN / SANITIZE / BLOCK |

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (with WSL2 backend on Windows)
- **NVIDIA GPU** (RTX 3050 or better) with latest drivers
- **Git**

### 1. Clone & Configure

```bash
git clone https://github.com/mouaad-here/Secure-RAG.git
cd Secure-RAG
cp .env.example .env
```

### 2. Start the Stack

```bash
docker compose up -d
```

This starts:
- **Ollama** (port 11434) — Local LLM server with GPU acceleration
- **API** (port 8000) — FastAPI application server

### 3. Pull AI Models (first time only)

```bash
docker exec rag-ollama ollama pull llama3.2:3b
docker exec rag-ollama ollama pull nomic-embed-text
```

### 4. Verify

```bash
# Health check
curl http://localhost:8000/health

# Open Swagger UI
# → http://localhost:8000/docs
```

**That's it!** Three commands and you're running. 🎉

---

## 🖥️ Hardware Configuration

This project is optimized for the **NVIDIA GeForce RTX 3050** (4GB VRAM):

| Setting | Value | Rationale |
|---------|-------|-----------|
| **LLM Model** | `llama3.2:3b` | Fits in 4GB VRAM with room for context |
| **Context Window** | 4096 tokens | RTX 3050 memory bandwidth handles this well |
| **Embedding Model** | `nomic-embed-text` | Lightweight, high-quality local embeddings |
| **GPU Acceleration** | CUDA enabled | Docker compose GPU passthrough configured |
| **Temperature** | 0.1 | Low for deterministic, factual responses |

### GPU Passthrough

The `docker-compose.yml` is pre-configured for NVIDIA GPU passthrough:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

> **Note:** Docker Desktop with WSL2 + NVIDIA drivers handles GPU passthrough natively on Windows. No separate NVIDIA Container Toolkit installation needed.

---

## 📁 Project Structure

```
Secure-RAG/
├── app/
│   ├── api/                    # FastAPI routes
│   │   ├── main.py             # App entry point + /health
│   │   ├── routes_ingest.py    # POST /ingest, GET /documents
│   │   └── routes_query.py     # POST /ask
│   ├── ingestion/              # Document processing pipeline
│   │   ├── loader.py           # PDF/MD/TXT loading
│   │   ├── normalizer.py       # Text cleaning
│   │   ├── chunker.py          # Text splitting
│   │   └── metadata.py         # Metadata builder
│   ├── security/               # Security layers
│   │   ├── scanner.py          # Input injection detection
│   │   ├── output_firewall.py  # Output sanitization
│   │   └── policy.py           # ALLOW/WARN/SANITIZE/BLOCK engine
│   ├── storage/                # Data persistence
│   │   ├── sqlite_store.py     # Document metadata + audit logs
│   │   ├── chroma_trusted.py   # Trusted document embeddings
│   │   └── chroma_quarantine.py# Quarantined document embeddings
│   ├── retrieval/              # Search & filtering
│   │   ├── embeddings.py       # Ollama embedding generation
│   │   ├── retriever.py        # Vector similarity search
│   │   └── filters.py          # Trust & relevance filtering
│   ├── generation/             # LLM interaction
│   │   ├── prompt_builder.py   # Hardened prompt templates
│   │   ├── ollama_client.py    # Ollama API client
│   │   └── citations.py        # Citation extraction & validation
│   └── config.py               # Pydantic settings
│
├── sample_docs/                # Clean test corpus
├── redteam_docs/               # Poisoned test corpus (5 attack types)
├── tests/                      # Unit & red-team tests
├── docker/                     # Dockerfiles (app + dev)
├── scripts/                    # Setup scripts
├── data/                       # Runtime data (gitignored)
├── docker-compose.yml          # Production compose (GPU enabled)
├── docker-compose.override.yml # Dev overrides (hot-reload)
└── .env.example                # Environment template
```

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health & config summary |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `POST` | `/api/v1/ingest` | Upload & process a document |
| `GET` | `/api/v1/documents` | List ingested documents |
| `POST` | `/api/v1/ask` | Ask a question (RAG pipeline) |

### Example: Ingest a Document

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@sample_docs/vacation_policy.md" \
  -F "source_label=hr_policies"
```

### Example: Ask a Question

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do I get per year?"}'
```

---

## 🧪 Testing

```bash
# Run all tests inside the container
docker compose exec api pytest

# Run only unit tests
docker compose exec api pytest tests/unit/

# Run with verbose output
docker compose exec api pytest -v --tb=long
```

---

## 📋 Daily Commands

```bash
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose logs -f api        # Tail API logs
docker compose logs -f ollama     # Tail Ollama logs
docker compose exec api bash      # Shell into API container
docker compose restart api        # Restart after code changes
docker compose build api          # Rebuild after Dockerfile changes
```

---

## 🌿 Git Workflow

We use **trunk-based development** with an integration branch:

```
main                    ← stable, tagged releases only
  └── integration/mvp   ← features tested together
        ├── feature/foundation
        ├── feature/ingestion
        ├── feature/security-scan
        └── ...
```

### Branch Convention

```bash
git checkout integration/mvp && git pull
git checkout -b feature/my-feature
# ... work, commit ...
git push -u origin feature/my-feature
# → Open PR targeting integration/mvp
```

### Commit Convention

```
feat(ingestion): add PDF loader with metadata extraction
fix(retrieval): handle empty quarantine collection
docs(readme): add docker setup instructions
test(security): add red-team test for indirect injection
```

---

## 🗺️ Roadmap

- [x] **Phase 0** — Foundation & Docker setup
- [ ] **Phase 1** — Baseline ingestion pipeline
- [ ] **Phase 2** — Baseline RAG (query → answer with citations)
- [ ] **Phase 3** — Security scanner integration
- [ ] **Phase 4** — Quarantine & trust filtering
- [ ] **Phase 5** — Output firewall
- [ ] **Phase 6** — Evaluation harness (Promptfoo + garak)
- [ ] **Phase 7** — API polish & documentation

---

## 📚 References

- [OWASP LLM Top 10 (2025)](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [RAG Security: The Forgotten Attack Surface](https://christian-schneider.net/blog/rag-security-forgotten-attack-surface/)
- [Promptfoo Documentation](https://www.promptfoo.dev/)
- [garak LLM Scanner](https://github.com/NVIDIA/garak)

---

## 📄 License

MIT
