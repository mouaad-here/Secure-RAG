# Spec: Phase 1 — Baseline Ingestion
# Branch: feature/ingestion
# Mode: BACKEND
# Owner: Core Dev
# DoD: `curl -F file=@sample_docs/handbook.pdf POST /ingest` populates SQLite

---

## Units

| # | Unit | File(s) |
|---|------|---------|
| 1.1 | Document Loader | `app/ingestion/loader.py` |
| 1.2 | Normalizer | `app/ingestion/normalizer.py` |
| 1.3 | Chunker | `app/ingestion/chunker.py` |
| 1.4 | Metadata Builder | `app/ingestion/metadata.py` |
| 1.5 | SQLite Store | `app/storage/sqlite_store.py` |
| 1.6 | Ingest Route | `app/api/routes_ingest.py` |
| 1.7 | Exceptions | `app/exceptions.py` |
| 1.8 | Tests | `tests/unit/test_loader.py`, `test_chunker.py`, `test_sqlite_store.py` |
| 1.9 | Read endpoints | `GET /api/v1/documents`, `GET /api/v1/documents/{id}` |

---

## Module Contracts

### `ingestion/loader.py`
- Accepts: `bytes`, `filename: str`, `source_label: str`
- Returns: `LoadedDocument` (already partially exists — review before rewriting)
- Supported types: `pdf`, `md`, `txt` only (registry dict)
- Raises: `UnsupportedFileTypeError` from `exceptions.py`

### `ingestion/normalizer.py`
- Accepts: `LoadedDocument`
- Returns: `str` (clean, whitespace-normalized text)
- Strips null bytes, excessive whitespace, BOM characters

### `ingestion/chunker.py`
- Uses: `langchain_text_splitters.RecursiveCharacterTextSplitter`
- chunk_size = `settings.max_chunk_size` (default 500)
- chunk_overlap = `settings.chunk_overlap` (default 50)
- Returns: `list[str]`

### `ingestion/metadata.py`
- Accepts: `LoadedDocument`, `trust_score: float`, `collection: str`, `chunk_count: int`, `flags: list[str]`
- Returns: `DocumentRecord` (Pydantic model matching SQLite schema)

### `storage/sqlite_store.py`
- Uses: SQLAlchemy Core (not ORM) with aiosqlite
- Tables: `documents`, `audit_log` (schema from ARCHITECTURE.md §5)
- Methods: `save_document()`, `get_document()`, `list_documents()`

### `api/routes_ingest.py`
- `POST /api/v1/ingest` — multipart file upload
  - Validate MIME type via extension (no python-magic in CI)
  - Call: loader → normalizer → chunker → sqlite_store (stub — no embedding yet)
  - Return: `IngestResponse` with doc_id, chunk_count, trust_score placeholder (1.0)
- `GET /api/v1/documents` — list all with collection status
- `GET /api/v1/documents/{doc_id}` — single document record

### `app/exceptions.py`
- `SecureRAGError(Exception)` — base
- `UnsupportedFileTypeError(SecureRAGError)`
- `DocumentLoadError(SecureRAGError)`
- `StorageError(SecureRAGError)`

---

## Layer Boundary Check
- `ingestion/` → may import `security/`, `storage/`, `config` ✅
- `storage/` → NO internal app imports ✅
- `api/` → may import `ingestion/`, `config` ✅

---

## New Dependencies
None — all required libs are already in `requirements.txt`.

---

## Verification
```bash
# From inside container:
docker compose exec api pytest tests/unit/test_loader.py tests/unit/test_chunker.py -v
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@sample_docs/vacation_policy.md" \
  | jq .
curl http://localhost:8000/api/v1/documents | jq .
```
Expected: 200 response with doc_id, chunk_count > 0.
