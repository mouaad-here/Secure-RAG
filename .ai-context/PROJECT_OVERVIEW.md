# PROJECT_OVERVIEW.md
# Secure Local RAG MVP

> Read this file at the start of EVERY Antigravity session.
> It defines what this system is, what it does, and what it will never do.

---

## 1. Product Purpose

**What is it?**
A fully local, defense-in-depth Retrieval-Augmented Generation (RAG) system
that allows users to query a private document corpus and receive cited,
grounded answers — with built-in protection against prompt injection,
data poisoning, and exfiltration attacks.

**Who uses it?**
Internal teams that need a private, auditable Q&A system over sensitive
documents (HR policies, legal documents, internal knowledge bases), where
data must never leave the local network and the system must be demonstrably
secure against adversarial document uploads.

**The core security thesis:**
Documents are not trusted by default. Every document passes through a
security scanner before being embedded. Suspicious content is quarantined
and never retrieved. LLM outputs are inspected before being returned.

---

## 2. Core Flows

### Flow A — Document Ingestion
```
User uploads file
  → FileTypeValidator (MIME check)
  → DocumentLoader (PDF / MD / TXT)
  → Normalizer (clean text extraction)
  → SecurityScanner (regex, URL, injection heuristics)
  → TrustScorer → score ∈ [0, 1]
  → if score ≥ TRUST_THRESHOLD → chroma_trusted + sqlite record
  → if score <  TRUST_THRESHOLD → chroma_quarantine + sqlite record (flagged)
  → Audit log (JSONL)
```

### Flow B — Query & Answer
```
User asks a question
  → QueryValidator (length, injection check)
  → EmbeddingGenerator (Ollama nomic-embed-text)
  → Retriever (top-k=5, queries ONLY chroma_trusted)
  → RiskFilter (secondary per-chunk check)
  → PromptBuilder (Jinja2 strict template)
  → OllamaClient (llama3.1:8b, fully local)
  → CitationBuilder (chunk refs → inline citations)
  → OutputFirewall (URL check, leak detection, groundedness)
  → PolicyEngine → ALLOW / WARN / SANITIZE / BLOCK
  → Final response + citations returned to user
  → Audit log (JSONL)
```

### Flow C — Evaluation (CI & manual)
```
pytest tests/unit/          → unit correctness
pytest tests/redteam/       → ASR, FPR, citation accuracy metrics
promptfoo run               → OWASP LLM Top 10 probes
garak                       → injection + hallucination probes
```

---

## 3. Simulation Scenario (MVP Context)

The MVP demonstrates security using a fictional "Company Policy Assistant":

**Clean corpus** (`sample_docs/`):
- `employee_handbook.pdf` — HR policies
- `vacation_policy.md` — PTO rules
- `it_security_rules.txt` — IT acceptable use
- `expense_policy.pdf` — reimbursement rules
- `remote_work_guide.md` — WFH policy

**Poisoned corpus** (`redteam_docs/`):
- Direct prompt injection payloads
- Hidden text (white-on-white in PDF) attacks
- Data exfiltration via URL injection
- Misinformation (subtle factual contradictions)
- Jailbreak roleplay attempts

---

## 4. Success Criteria (MVP Done When)

| # | Criterion | Target |
|---|-----------|--------|
| 1 | Clean questions → correct, cited answers | 5/5 |
| 2 | Poisoned docs flagged at ingestion | 5/5 |
| 3 | Output firewall catches force-injected poison | ✅ |
| 4 | Attack Success Rate (ASR) | < 10% |
| 5 | False Positive Rate (FPR) | < 15% |
| 6 | Citation accuracy | > 90% |
| 7 | Runs offline via `docker compose up` | ✅ |
| 8 | New teammate onboarded in < 15 minutes | ✅ |

---

## 5. Out-of-Scope for MVP (Do Not Build)

These items are explicitly deferred. Do not implement, stub, or partially
build them during the MVP phase.

| Category | Out of Scope Item |
|----------|-------------------|
| Auth | User authentication, JWT, API keys, multi-tenant isolation |
| UI | Web frontend, dashboard, chat UI |
| Cloud | Any cloud LLM API (OpenAI, Anthropic, etc.) |
| Cloud | Any cloud storage (S3, GCS, Azure Blob) |
| Scale | Horizontal scaling, load balancing, Redis |
| Database | PostgreSQL, MongoDB — SQLite is sufficient |
| Streaming | SSE / WebSocket streaming responses |
| Admin | Document management UI, quarantine review workflow |
| File types | DOCX, XLSX, images, HTML (only PDF / MD / TXT for MVP) |
| Monitoring | Prometheus, Grafana, alerting |

**When a future extension is discussed**, document it here under a new
"Future Extensions" section and note it in `PROGRESS_TRACKER.md`.
Do not add code for it.

---

## 6. Project Milestones (Release Tags)

| Tag | What it represents |
|-----|-------------------|
| `v0.1-baseline-rag` | Working RAG, no security |
| `v0.2-secure-ingestion` | Scanner + quarantine complete |
| `v0.3-output-firewall` | Output security layer complete |
| `v1.0-mvp` | Full system + eval harness, demo-ready |

---

## 7. Team & Ownership

| Role | Responsibility |
|------|---------------|
| Security Dev | `app/security/`, red-team corpus, evaluation harness |
| Core Dev | `app/ingestion/`, `app/storage/`, `app/retrieval/` |
| All | `app/api/`, `app/generation/`, documentation |

---

*Last updated: 2025-05-15 | Read by Antigravity at session start*
