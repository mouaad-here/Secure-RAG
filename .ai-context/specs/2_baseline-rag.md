# Spec: Phase 2 — Baseline RAG
# Branch: feature/baseline-rag
# Mode: BACKEND
# Owner: Core Dev (1–2 devs, parallel possible)
# DoD: "How many vacation days?" returns a cited answer
# Tag at close: v0.1-baseline-rag

---

## Units

| # | Unit | File(s) |
|---|------|---------|
| 2.1 | Embeddings | `app/retrieval/embeddings.py` |
| 2.2 | Chroma Trusted Store | `app/storage/chroma_trusted.py` |
| 2.3 | Retriever | `app/retrieval/retriever.py` |
| 2.4 | Prompt Builder | `app/generation/prompt_builder.py` |
| 2.5 | Ollama Client | `app/generation/ollama_client.py` |
| 2.6 | Citations | `app/generation/citations.py` |
| 2.7 | Query Route | `app/api/routes_query.py` — wire `POST /ask` |
| 2.8 | Tests | `test_retriever.py`, `test_prompt_builder.py` |
| 2.9 | Wire embeddings into ingest | Update `routes_ingest.py` to embed after chunk |

---

## Module Contracts

### `retrieval/embeddings.py`
- `EmbeddingGenerator` class with `BaseLLMClient`-style interface
- `generate(text: str) -> list[float]`
- `generate_batch(texts: list[str]) -> list[list[float]]`
- Uses: `ollama.Client(host=settings.ollama_host).embeddings(model=settings.embedding_model)`

### `storage/chroma_trusted.py`
- `ChromaTrustedStore` class
- `add_chunks(doc_id, chunks, embeddings, metadata_list) -> None`
- `query(embedding, top_k) -> list[ChunkResult]`
- Persistent at `settings.chroma_persist_dir/trusted`
- Collection name: `"trusted_chunks"`

### `retrieval/retriever.py`
- `Retriever` class
- `retrieve(query: str, top_k: int = 5) -> list[ChunkResult]`
- Flow: generate query embedding → query chroma_trusted → return results
- NEVER queries quarantine collection

### `generation/prompt_builder.py`
- Jinja2 template — strict, no free-form injection
- Template: system instruction + retrieved chunks with indices + user question
- `build_prompt(question: str, chunks: list[ChunkResult]) -> str`
- Template stored as string constant in module (no external file)

### `generation/ollama_client.py`
- `BaseLLMClient` abstract base class
- `OllamaClient(BaseLLMClient)` implementation
- `complete(prompt: str) -> str`
- Uses: `ollama.Client(host=settings.ollama_host).generate(...)`
- Timeout: 60s default

### `generation/citations.py`
- `build_citations(chunks: list[ChunkResult]) -> list[Citation]`
- `Citation`: source_file, chunk_index, excerpt (first 100 chars)
- `format_response(answer: str, citations: list[Citation]) -> QueryResponse`

### `api/routes_query.py` (update)
- `POST /api/v1/ask`
  - Input: `QueryRequest(question: str)` — validate length, not empty
  - Flow: retriever → prompt_builder → ollama_client → citations → output (no firewall yet)
  - Return: `QueryResponse(answer, citations, retrieval_count)`

---

## Layer Boundary Check
- `retrieval/` → may import `storage/`, `config` ✅
- `generation/` → may import `retrieval/` (read), `config` ✅
- `api/` → may import `generation/`, `retrieval/`, `config` ✅
- `storage/` → NO internal imports ✅

---

## New Dependencies
None — `chromadb`, `ollama`, `jinja2` already in `requirements.txt`.

---

## Security Note
Phase 2 has NO security layer yet — that is Phase 3.
The `/ask` endpoint at this stage returns raw LLM output.
This is intentional (baseline). Do not add scanner/firewall yet.

---

## Verification
```bash
# Seed a doc first (Phase 1 must be done)
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@sample_docs/vacation_policy.md"

# Ask a question
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do I get per year?"}' \
  | jq .

# Expected: answer string + citations array with source_file references
```
Tag commit: `git tag -a v0.1-baseline-rag -m "Baseline RAG without security"`
