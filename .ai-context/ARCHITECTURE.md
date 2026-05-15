# ARCHITECTURE.md
# Secure Local RAG MVP — Technical Architecture

> Read this file at the start of EVERY Antigravity session.
> These are binding architectural decisions. Changes require team approval
> and must be logged in PROGRESS_TRACKER.md under "Architecture Decisions."

---

## 1. Runtime Environment

| Property | Value |
|----------|-------|
| Language | Python 3.11 |
| Container | Docker + Docker Compose (always) |
| Network | Fully local, no external API calls (offline-first) |
| OS target | Linux (Docker). Dev on macOS/Windows via Docker Desktop |
| Min RAM | 8 GB (Ollama model + API + ChromaDB) |
| GPU | Optional. Ollama auto-detects. CPU fallback is supported |

---

## 2. Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT LAYER          app/api/                                 │
│  FastAPI + Uvicorn · REST · Swagger auto-docs · Pydantic I/O   │
└──────────┬────────────────────────────┬────────────────────────┘
           │ Upload                      │ Query
┌──────────▼──────────┐      ┌──────────▼──────────────────────┐
│  INGESTION LAYER    │      │  RETRIEVAL LAYER                 │
│  app/ingestion/     │      │  app/retrieval/                  │
│  loader.py          │      │  embeddings.py (nomic-embed)     │
│  normalizer.py      │      │  retriever.py (top-k, trusted)  │
│  chunker.py         │      │  filters.py (risk check)         │
│  metadata.py        │      └──────────────┬───────────────────┘
└──────────┬──────────┘                     │
           │                                │
┌──────────▼────────────────────────────────▼───────────────────┐
│  SECURITY LAYER    app/security/                               │
│  scanner.py · output_firewall.py · policy.py · patterns.py    │
│  (No internal imports — pure logic, tested in isolation)       │
└──────────┬────────────────────────────────┬───────────────────┘
           │                                │
┌──────────▼────────────────────────────────▼───────────────────┐
│  STORAGE LAYER    app/storage/                                 │
│  sqlite_store.py (metadata + audit log)                        │
│  chroma_trusted.py (clean chunks only)                         │
│  chroma_quarantine.py (flagged chunks, never retrieved)        │
└────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────┐
│  GENERATION LAYER    app/generation/                            │
│  prompt_builder.py (Jinja2 strict template)                    │
│  ollama_client.py (BaseLLMClient interface)                    │
│  citations.py (chunk ref → inline citation)                    │
└─────────────────────────┬──────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────┐
│  OUTPUT SECURITY LAYER    app/security/output_firewall.py      │
│  URL scanner · leak detector · groundedness check              │
│  Policy engine: ALLOW | WARN | SANITIZE | BLOCK                │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Dependency Rules (Invariants)

These are hard constraints enforced by code review and linting.

```
api/         → may import: ingestion/, retrieval/, generation/, security/, config
ingestion/   → may import: security/, storage/, config
retrieval/   → may import: storage/, security/, config
generation/  → may import: retrieval/ (read), security/, config
security/    → NO internal app imports (only stdlib + external libs + config)
storage/     → NO internal app imports (only stdlib + external libs + config)
config.py    → NO internal app imports
```

**Critical forbidden imports:**
- `api/` must never import `storage/` directly
- `generation/` must never write to `storage/`
- `security/` must never import from ingestion, retrieval, or generation

---

## 4. Technology Stack

### Core Services

| Service | Image / Runtime | Port | Data |
|---------|----------------|------|------|
| API | `python:3.11-slim` (custom) | 8000 | stateless |
| Ollama | `ollama/ollama:latest` | 11434 | `ollama_data` Docker volume |
| ChromaDB | embedded (in API process) | — | `./data/chroma/` host mount |
| SQLite | embedded (in API process) | — | `./data/sqlite/app.db` host mount |

### Python Libraries (locked in `requirements.txt`)

| Library | Purpose | Layer |
|---------|---------|-------|
| `fastapi` | HTTP framework | api |
| `uvicorn` | ASGI server | api |
| `pydantic-settings` | Config + env validation | config |
| `pypdf` | PDF text extraction | ingestion |
| `python-magic` | MIME type detection | ingestion |
| `unstructured` | Rich document parsing | ingestion |
| `langchain-text-splitters` | RecursiveCharacterTextSplitter | ingestion |
| `chromadb` | Vector store (embedded) | storage |
| `sqlalchemy` | SQLite ORM | storage |
| `ollama` (Python client) | Embeddings + LLM calls | retrieval, generation |
| `Jinja2` | Prompt template rendering | generation |
| `rebuff` | Prompt injection heuristics | security |
| `tldextract` | URL domain extraction | security |
| `structlog` | Structured JSON logging | all |
| `pytest` | Test runner | tests |

---

## 5. Data Model

### SQLite Tables

```sql
-- Document records
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,     -- UUID
    filename    TEXT NOT NULL,
    file_type   TEXT NOT NULL,        -- pdf | md | txt
    owner_id    TEXT,                 -- NULL for MVP; used in multi-tenant future
    trust_score REAL NOT NULL,        -- 0.0–1.0
    collection  TEXT NOT NULL,        -- 'trusted' | 'quarantine'
    ingested_at TEXT NOT NULL,        -- ISO 8601
    chunk_count INTEGER NOT NULL,
    scan_flags  TEXT                  -- JSON array of flag names
);

-- Audit log (mirrored from JSONL)
CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,         -- ingest | query | block | warn
    doc_id     TEXT,
    query_hash TEXT,                  -- SHA256 of query, not raw text
    policy     TEXT,                  -- ALLOW | WARN | SANITIZE | BLOCK
    created_at TEXT NOT NULL
);
```

### ChromaDB Collections

| Collection | Contains | Queried at runtime? |
|------------|----------|---------------------|
| `trusted_chunks` | Clean, scored ≥ TRUST_THRESHOLD | Yes |
| `quarantine_chunks` | Flagged, scored < TRUST_THRESHOLD | No (debug only) |

Each chunk document metadata:
```json
{
  "doc_id": "uuid",
  "chunk_index": 0,
  "trust_score": 0.92,
  "source_file": "vacation_policy.md",
  "char_offset": 1240,
  "owner_id": null
}
```

---

## 6. Security Architecture

### Defense Layers (in order)

| Layer | Defense | Catches |
|-------|---------|---------|
| 1 | MIME validation | Wrong file type masquerading |
| 2 | Security scanner (input) | Injection patterns, malicious URLs |
| 3 | Trust scoring | Low-confidence / adversarial content |
| 4 | Quarantine storage | Poisoned content isolated at rest |
| 5 | Retriever filter | Only trusted chunks leave storage |
| 6 | Prompt template | Strict structure limits injection surface |
| 7 | Output firewall | URL exfiltration, leaked instructions |
| 8 | Policy engine | Final ALLOW/BLOCK decision with logging |

### Trust Score Computation (v1)

```python
# Heuristic, not ML — fast and auditable
score = 1.0
score -= weight_injection_patterns * injection_count
score -= weight_url_count * (url_count_outside_allowlist / max(url_count, 1))
score -= weight_entropy * normalized_entropy_anomaly
score = max(0.0, min(1.0, score))
```

All weights are config-driven. Score is stored; algorithm is versioned
in `security/scanner.py` docstring.

---

## 7. Configuration (pydantic-settings)

All config lives in `app/config.py` as a `Settings` class.
All values come from environment variables. Defaults are safe.

```python
class Settings(BaseSettings):
    # LLM
    ollama_host: str = "http://ollama:11434"
    llm_model: str = "llama3.1:8b"
    embedding_model: str = "nomic-embed-text"

    # Storage
    chroma_persist_dir: str = "/app/data/chroma"
    sqlite_path: str = "/app/data/sqlite/app.db"
    log_dir: str = "/app/data/logs"

    # Security
    trust_threshold: float = 0.7      # Below this → quarantine
    url_allowlist: list[str] = []
    max_chunk_size: int = 500
    chunk_overlap: int = 50

    # API
    api_port: int = 8000
    log_level: str = "INFO"
```

---

## 8. Logging Architecture

All logs are structured JSON via `structlog`. Two sinks:

1. **JSONL files** at `LOG_DIR/audit_YYYY-MM-DD.jsonl` — one event per line
2. **SQLite `audit_log` table** — queryable summary

Log events (never log raw text content at INFO+):
```json
{"event": "ingest_complete", "doc_id": "...", "trust_score": 0.84, "collection": "trusted"}
{"event": "query_blocked", "query_hash": "sha256:...", "reason": "output_firewall", "policy": "BLOCK"}
{"event": "chunk_quarantined", "doc_id": "...", "chunk_index": 3, "flags": ["injection_pattern"]}
```

---

## 9. Extension Points (Future-Ready, Not Implemented)

| Extension | Prepared Via |
|-----------|-------------|
| Swap ChromaDB for pgvector/Pinecone | `storage/` abstraction + `BaseVectorStore` interface |
| Swap Ollama for other local LLMs | `BaseLLMClient` interface in `ollama_client.py` |
| Add more file types | Loader registry dict in `loader.py` |
| Multi-tenant | `owner_id` field on all records (nullable MVP) |
| Auth middleware | FastAPI middleware slot in `main.py` (commented placeholder) |
| Plugin scanners | `List[ScannerPlugin]` in `scanner.py` |

---

*Last updated: 2025-05-15 | Architecture Owner: Team | Agent: Antigravity*
