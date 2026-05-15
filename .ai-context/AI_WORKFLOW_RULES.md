# AI_WORKFLOW_RULES.md
# Secure Local RAG MVP — Antigravity Workflow Protocol

> Read this file at the start of EVERY Antigravity session.
> These are operational rules for how Antigravity executes work.
> They exist because security projects punish guessing and reward precision.

---

## 1. The Session Protocol

Every Antigravity session follows this sequence. No exceptions.

```
STEP 1 — READ CONTEXT (mandatory before anything else)
  Read all 6 files in .ai-context/ in order.
  State: current phase, current unit, last completed unit.
  Wait for user to confirm before proceeding.

STEP 2 — UNDERSTAND THE UNIT
  Read the current unit from PROGRESS_TRACKER.md.
  If the unit is ambiguous, ask ONE clarifying question. Do not guess.
  State your plan for the unit in ≤ 5 bullet points.
  Wait for user to confirm the plan.

STEP 3 — EXECUTE ONE UNIT
  Write code for the single confirmed unit only.
  Follow all rules in CODE_STANDARDS.md.
  Enforce all boundaries from ARCHITECTURE.md.

STEP 4 — VERIFY
  State what tests cover this unit.
  Write or update the relevant test file.
  List any new environment variables and confirm they are in .env.example.

STEP 5 — CLOSE
  Update PROGRESS_TRACKER.md: mark the unit done.
  State the next unit clearly.
  Stop. Do not start the next unit in the same session unless user asks.
```

---

## 2. The One-Unit Rule

**One unit = one checklist bullet in the current phase.**

| Allowed in one session | Not allowed |
|------------------------|-------------|
| Implement `loader.py` | Implement `loader.py` AND `normalizer.py` |
| Write tests for `scanner.py` | Write scanner + tests + update retriever |
| Fix a bug in `output_firewall.py` | Fix bug + add new feature |
| Add one new pattern to `patterns.py` | Add patterns + refactor scanner |

**The only exception:** if a unit truly cannot be tested in isolation
without a trivial stub in another module, you may add the minimal stub
(≤ 10 lines) and document it as a stub in a `# STUB:` comment.

---

## 3. What to Do When Uncertain

**Never guess on security decisions.**

| Situation | Correct Action |
|-----------|---------------|
| Unsure if a pattern is safe | Stop. Ask. Document the question in the chat. |
| Two valid implementations exist | Present both options with trade-offs. Wait for decision. |
| A new dependency seems useful | Propose it. Do not add it to requirements.txt until approved. |
| An architectural boundary might need to change | Stop. Raise it explicitly. Do not work around it. |
| A test case is hard to write | Write it anyway. Difficulty = important edge case. |
| The unit scope is unclear | Ask ONE question to clarify. Do not interpret broadly. |

---

## 4. Small Steps Philosophy

Prefer **3 small correct steps** over **1 large ambitious step**.

```
✅ Good unit size:
   "Implement the URL extractor in security/scanner.py"
   → 1 function, 20–30 lines, tested in isolation

❌ Too large:
   "Implement the full security scanner"
   → Would touch scanner.py, patterns.py, tests, maybe output_firewall.py
   → Split into: url_extractor → injection_checker → trust_scorer → integrate
```

If you realize mid-execution that a unit is larger than expected:
1. Stop.
2. Report: "This unit is larger than expected. I suggest splitting it into: [list]."
3. Wait for user to choose the split.

---

## 5. Security Decision Checkpoints

Before writing any code that touches these areas, **pause and state your
intent** so the user can review before you proceed:

- Modifying trust score computation logic
- Changing which ChromaDB collection is queried
- Modifying the output firewall's BLOCK/ALLOW decision
- Adding or removing a regex pattern in `patterns.py`
- Changing the Jinja2 prompt template
- Adding a new field to the audit log
- Changing `TRUST_THRESHOLD` default or loading logic
- Any change to `chroma_trusted` vs `chroma_quarantine` routing

Format: _"I am about to [action]. This affects [security property].
My approach is [explanation]. Shall I proceed?"_

---

## 6. Code Quality Gates (before declaring a unit done)

Antigravity must self-check these before marking any unit complete:

- [ ] All new functions have type hints
- [ ] All new functions have docstrings
- [ ] No hardcoded values (use `settings.*` or constants)
- [ ] New security logic has corresponding tests in `tests/unit/`
- [ ] No raw document text logged at INFO level
- [ ] No new imports that aren't in `requirements.txt`
- [ ] No layer boundary violations (check ARCHITECTURE.md §3)
- [ ] `eval()`, `exec()`, `subprocess.shell=True` not used
- [ ] New env vars documented in `.env.example` with a comment
- [ ] File length < 200 lines, function length < 40 lines

---

## 7. Handling Contradictions

If a user request contradicts a rule in this document or in
`ARCHITECTURE.md` / `CODE_STANDARDS.md`:

1. **Do not silently comply.**
2. State the contradiction clearly:
   _"You asked for X, but CODE_STANDARDS.md requires Y. 
   To do X, we'd need to update the standard. Should we?"_
3. Wait for an explicit decision.
4. If the decision is to update the standard, update the file and log
   the change in `PROGRESS_TRACKER.md` under "Architecture Decisions."

---

## 8. Working with Red-Team Artifacts

`redteam_docs/` contains real adversarial payloads for testing.
When working with these:

- Never copy payload text verbatim into production code (even as comments).
- Tests that use payloads reference them via file path or sanitized labels,
  not inline in the test source.
- Red-team test functions are tagged `@pytest.mark.redteam`.
- Never commit new payloads without a comment describing the attack class.

---

## 9. Evaluation Metrics — What "Done" Means

A security feature is not done when the code is written.
It is done when **metrics confirm it works**:

| Feature | Done When |
|---------|----------|
| Security scanner | `pytest tests/unit/test_scanner.py` passes all TP/TN cases |
| Quarantine routing | No quarantined content appears in `/ask` responses (test) |
| Output firewall | Force-injected chunk is caught and BLOCK policy fires |
| Full evaluation | `pytest tests/redteam/` produces report with ASR < 10%, FPR < 15% |

Do not mark a phase complete until its definition of done is met.

---

## 10. What Antigravity Will Say (Prompt Prefixes)

To make sessions predictable, Antigravity uses these prefixes:

| Prefix | Meaning |
|--------|---------|
| `[BOOT]` | Reading context files |
| `[PLAN]` | Presenting a plan for a unit (awaiting confirmation) |
| `[CHECKPOINT]` | Security decision pause (awaiting confirmation) |
| `[CODE]` | Writing code |
| `[TEST]` | Writing or updating tests |
| `[VERIFY]` | Self-checking quality gates |
| `[UPDATE]` | Updating PROGRESS_TRACKER.md |
| `[QUESTION]` | Asking a clarifying question (max 1 per situation) |
| `[WARN]` | Flagging a rule violation or concern |

---

*Last updated: 2025-05-15 | Protocol Owner: Team | Agent: Antigravity*
