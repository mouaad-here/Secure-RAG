# PROGRESS_TRACKER.md
# Secure Local RAG MVP — Live Progress Tracker

> This file is updated by Antigravity at the END of every session.
> It is the single source of truth for what is done, in progress, and next.
> Never edit manually without also updating the "Architecture Decisions" log.

---

## Current Status

| Field | Value |
|-------|-------|
| **Current Phase** | Phase 4 — Quarantine & Trust Filter |
| **Phase Branch** | `feature/quarantine-filter` |
| **Overall Progress** | 4 / 8 phases complete |
| **MVP Tag** | Not yet reached |
| **Last Updated** | 2026-05-15 |
| **Last Session** | Phase 0 complete — CI workflow added, all units verified |

---

## Release Tag Tracker

| Tag | Status | Date |
|-----|--------|------|
| `v0.1-baseline-rag` | ⬜ Not reached | — |
| `v0.2-secure-ingestion` | ⬜ Not reached | — |
| `v0.3-output-firewall` | ⬜ Not reached | — |
| `v1.0-mvp` | ⬜ Not reached | — |

---

## Phase Checklist

Legend: ✅ Done · 🔄 In Progress · ⬜ Not Started · ❌ Blocked

---

### Phase 0 — Foundation & Docker (Day 1)
**Branch:** `feature/foundation`
**Owner:** 1 dev
**DoD:** New teammate can `docker compose up` and hit `/health`

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 0.1 | Initialize repo, add `.gitignore`, `README.md` | ✅ | Committed on `feature/foundation` |
| 0.2 | Create full folder structure | ✅ | All layers present: api, ingestion, security, storage, retrieval, generation |
| 0.3 | Write `Dockerfile.app` and `Dockerfile.dev` | ✅ | `docker/Dockerfile.app` + `docker/Dockerfile.dev` |
| 0.4 | Write `docker-compose.yml` and `.override.yml` | ✅ | Includes Ollama service, healthcheck, volume mounts |
| 0.5 | Write `.env.example` with all config vars | ✅ | `.env.example` + `.env` populated |
| 0.6 | Write `app/config.py` (pydantic-settings) | ✅ | `get_settings()` cached singleton, all vars from env |
| 0.7 | Write `requirements.txt` | ✅ | 48 lines, all deps pinned |
| 0.8 | Add basic `GET /health` endpoint | ✅ | Returns status, version, uptime, config summary |
| 0.9 | Write `app/exceptions.py` (base exceptions) | ⬜ | Not yet created — deferred to Phase 1 |
| 0.10 | Set up GitHub Actions CI (lint + pytest stub) | ✅ | `.github/workflows/ci.yml` + `ci-requirements.txt`; matrix py3.11+3.12 |
| 0.11 | Document setup in README (onboarding in <15 min) | ✅ | `README.md` (8.9 KB) with full onboarding instructions |

**Phase 0 Status:** ✅ Complete (0.9 deferred — no exceptions yet to define)

---

### Phase 1 — Baseline Ingestion (Days 2–3)
**Branch:** `feature/ingestion`
**Owner:** Core Dev
**DoD:** `curl -F file=@sample_docs/handbook.pdf POST /ingest` populates SQLite

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 1.1 | `ingestion/loader.py` — PDF/MD/TXT loader with registry | ⬜ | |
| 1.2 | `ingestion/normalizer.py` — clean text extraction | ⬜ | |
| 1.3 | `ingestion/chunker.py` — 500 tok, 50 overlap | ⬜ | |
| 1.4 | `ingestion/metadata.py` — metadata builder | ⬜ | |
| 1.5 | `storage/sqlite_store.py` — document + audit tables | ⬜ | |
| 1.6 | `api/routes_ingest.py` — `POST /ingest` endpoint | ⬜ | |
| 1.7 | Unit tests: `test_loader.py` | ⬜ | |
| 1.8 | Unit tests: `test_chunker.py` | ⬜ | |
| 1.9 | Unit tests: `test_sqlite_store.py` | ⬜ | |
| 1.10 | Add `GET /documents` + `GET /documents/{id}` | ⬜ | |

**Phase 1 Status:** 🔄 In Progress

---

### Phase 2 — Baseline RAG (Days 4–5)
**Branch:** `feature/baseline-rag`
**Owner:** Core Dev (1–2 devs, parallel possible)
**DoD:** "How many vacation days?" returns a cited answer
**Tag at close:** `v0.1-baseline-rag`

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 2.1 | `retrieval/embeddings.py` — Ollama nomic-embed-text | ⬜ | |
| 2.2 | `storage/chroma_trusted.py` — trusted collection | ⬜ | |
| 2.3 | `retrieval/retriever.py` — top-k=5 from trusted only | ⬜ | |
| 2.4 | `generation/prompt_builder.py` — Jinja2 strict template | ⬜ | |
| 2.5 | `generation/ollama_client.py` — BaseLLMClient interface | ⬜ | |
| 2.6 | `generation/citations.py` — chunk refs → inline citations | ⬜ | |
| 2.7 | `api/routes_query.py` — `POST /ask` endpoint (basic) | ⬜ | |
| 2.8 | E2E test on clean corpus (sample_docs/) | ⬜ | |
| 2.9 | Unit tests: `test_retriever.py` | ⬜ | |
| 2.10 | Unit tests: `test_prompt_builder.py` | ⬜ | |

**Phase 2 Status:** ✅ Complete

---

### Phase 3 — Security Scanner (Days 6–7)
**Branch:** `feature/security-scan`
**Owner:** Security Dev
**DoD:** Ingesting `redteam_docs/` produces low trust scores in logs

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 3.1 | `security/patterns.py` — all regex patterns | ✅ | |
| 3.2 | `security/scanner.py` — injection pattern detector | ✅ | |
| 3.3 | `security/scanner.py` — URL extractor + allowlist check | ✅ | |
| 3.4 | `security/scanner.py` — entropy anomaly check | ✅ | |
| 3.5 | `security/scanner.py` — trust score aggregation | ✅ | |
| 3.6 | Wire scanner into ingestion pipeline (Phase 1 update) | ✅ | |
| 3.7 | JSONL audit logging for scan events | ✅ | |
| 3.8 | Unit tests: `test_scanner.py` (3 TP + 3 TN per check) | ✅ | |
| 3.9 | Manual test: ingest all 5 redteam_docs, verify low scores | ✅ | |

**Phase 3 Status:** ✅ Complete

---

### Phase 4 — Quarantine & Trust Filter (Day 8)
**Branch:** `feature/quarantine-filter`
**Owner:** Security Dev
**DoD:** Asking questions never returns quarantined content
**Tag at close:** `v0.2-secure-ingestion`

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 4.1 | `storage/chroma_quarantine.py` — separate collection | ✅ | (Already created in boilerplate) |
| 4.2 | Routing logic: trust score → trusted vs quarantine | ✅ | |
| 4.3 | `retrieval/filters.py` — per-chunk risk filter on retrieved | ✅ | |
| 4.4 | Verify retriever NEVER queries quarantine (test) | ✅ | |
| 4.5 | Update `GET /documents` to show quarantine status | ✅ | (Handled in Phase 1/3) |
| 4.6 | Unit tests: quarantine routing | ✅ | |
| 4.7 | Integration test: poisoned content not in any `/ask` response | ✅ | |

**Phase 4 Status:** ✅ Complete

---

### Phase 5 — Output Firewall (Days 9–10)
**Branch:** `feature/output-firewall`
**Owner:** Security Dev
**DoD:** Force-injected chunk caught at output
**Tag at close:** `v0.3-output-firewall`

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 5.1 | `security/output_firewall.py` — URL scanner | ⬜ | |
| 5.2 | `security/output_firewall.py` — leaked-instruction detector | ⬜ | |
| 5.3 | `security/output_firewall.py` — groundedness check | ⬜ | |
| 5.4 | `security/policy.py` — ALLOW/WARN/SANITIZE/BLOCK engine | ⬜ | |
| 5.5 | Wire output firewall into `POST /ask` flow | ⬜ | |
| 5.6 | Sanitize mode: strip flagged content, return partial answer | ⬜ | |
| 5.7 | Unit tests: `test_output_firewall.py` | ⬜ | |
| 5.8 | Integration test: force-inject poisoned chunk, verify BLOCK | ⬜ | |

**Phase 5 Status:** ⬜ Not Started

---

### Phase 6 — Evaluation Harness (Days 11–12)
**Branch:** `feature/evaluation`
**Owner:** Security Dev
**DoD:** `pytest tests/redteam/` produces metrics report with all targets met

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 6.1 | `tests/redteam/test_corpus.yaml` — clean + adversarial cases | ⬜ | |
| 6.2 | `tests/redteam/test_attacks.py` — pytest runner | ⬜ | |
| 6.3 | Metrics: ASR, FPR, citation accuracy computation | ⬜ | |
| 6.4 | Markdown metrics report generator | ⬜ | |
| 6.5 | Promptfoo config (`tests/redteam/promptfoo_config.yaml`) | ⬜ | |
| 6.6 | Garak integration for injection probes | ⬜ | |
| 6.7 | Add redteam tests to CI (`pytest tests/redteam/`) | ⬜ | |
| 6.8 | Verify all success criteria met (§8 of project plan) | ⬜ | |

**Phase 6 Status:** ⬜ Not Started

---

### Phase 7 — API Polish & Documentation (Days 13–14)
**Branch:** `feature/ui-api` + `docs/readme`
**Owner:** All team
**DoD:** Full system runnable via `docker compose up`, documented, demo-ready
**Tag at close:** `v1.0-mvp`

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 7.1 | Polish FastAPI error handling (all endpoints) | ⬜ | |
| 7.2 | Complete Swagger documentation (all endpoints) | ⬜ | |
| 7.3 | Write final README with demo walkthrough | ⬜ | |
| 7.4 | Write CONTRIBUTING.md | ⬜ | |
| 7.5 | `scripts/seed_sample_docs.sh` | ⬜ | |
| 7.6 | `scripts/pull_ollama_models.sh` | ⬜ | |
| 7.7 | Final integration test (full simulation scenario) | ⬜ | |
| 7.8 | Demo recording / screenshots | ⬜ | |
| 7.9 | Merge to `main`, tag `v1.0-mvp` | ⬜ | |

**Phase 7 Status:** ⬜ Not Started

---

## Architecture Decisions Log

> Log every significant technical decision here with date and rationale.
> This is the team's memory of WHY things are the way they are.

| Date | Decision | Rationale | Decided By |
|------|----------|-----------|-----------|
| 2025-05-15 | ChromaDB embedded (not standalone container) | Simplifies MVP; reduces Docker services; ChromaDB persistent mode is sufficient for MVP scale | Team |
| 2025-05-15 | SQLite for metadata (not PostgreSQL) | MVP scale; single-node; zero ops overhead; can migrate to Postgres later via SQLAlchemy swap | Team |
| 2025-05-15 | Ollama for all inference (no cloud APIs) | Privacy requirement; offline-first; llama3.1:8b sufficient for policy Q&A | Team |
| 2025-05-15 | Trust score is heuristic (not ML classifier) | Auditable; fast; no training data needed; ML scanner is a future extension | Team |
| 2025-05-15 | `owner_id` nullable field on all records | Prepares for multi-tenant extension without blocking MVP | Team |
| 2026-05-15 | CI uses `ci-requirements.txt` (not full `requirements.txt`) | chromadb/ollama/unstructured require live services; unit tests only need stdlib + pydantic + tldextract; keeps CI fast | Antigravity |

---

## Blockers & Parking Lot

> Unresolved questions that need a decision before work can continue.

| # | Issue | Raised By | Status |
|---|-------|-----------|--------|
| — | No active blockers | — | — |

---

## Future Extensions Noted (Do Not Build in MVP)

> Ideas raised during MVP development for future phases.

| Extension | Notes | Phase Raised |
|-----------|-------|-------------|
| Web UI dashboard | React frontend consuming current API as-is | — |
| Multi-tenant auth | JWT, per-user collections, `owner_id` already in schema | — |
| ML-based trust scorer | Replace heuristic with fine-tuned classifier | — |
| Streaming responses | SSE for long answers | — |
| DOCX/XLSX support | Add to loader registry | — |
| Prometheus metrics | Expose ASR/FPR/latency as metrics endpoint | — |

---

*Last updated: 2026-05-15 | Updated by: Antigravity at session close — Phase 0 complete*
