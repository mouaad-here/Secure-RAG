# CODE_STANDARDS.md
# Secure Local RAG MVP — Code Standards & Conventions

> Read this file at the start of EVERY Antigravity session.
> These standards apply to every line of code written or modified.

---

## 1. Language & Version

- **Python 3.11** strictly. No 3.10 or 3.12 features.
- Use `from __future__ import annotations` in all files for forward refs.
- No walrus operators (`:=`) in public API code (readability for new devs).

---

## 2. File Organization

### Module Template

Every new Python file must start with this header:

```python
"""
<module name> — <one-line description>

Layer: <api | ingestion | security | storage | retrieval | generation>
Imports allowed: <list per ARCHITECTURE.md Layer Dependency Rules>
"""
from __future__ import annotations
```

### File Size Limits
- **200 lines max** per file (excluding docstrings and blank lines).
- If a file approaches 200 lines, split it before it hits the limit.
- Split strategy: extract a helper module named `<original>_utils.py`
  or group by sub-concept.

### Directory Structure (do not create new top-level dirs without approval)

```
app/
├── api/              # HTTP layer only
├── ingestion/        # Document processing pipeline
├── security/         # All security logic (input + output)
├── storage/          # Persistence abstractions
├── retrieval/        # Vector search + filtering
├── generation/       # LLM calls + prompt building
└── config.py         # Single settings object

tests/
├── unit/             # One file per module: test_<module>.py
└── redteam/          # YAML corpus + attack test scripts
```

---

## 3. Type Hints

Type hints are **required** on all function signatures. No exceptions.

```python
# ✅ Correct
def scan_chunk(text: str, patterns: list[re.Pattern]) -> ScanResult:
    ...

# ❌ Wrong — missing hints
def scan_chunk(text, patterns):
    ...
```

- Use `list[str]` not `List[str]` (Python 3.9+ built-in generics).
- Use `dict[str, Any]` not `Dict[str, Any]`.
- Avoid `Any`. If unavoidable, add a comment: `# type: ignore[...] — reason`.
- Use `TypedDict` for structured dicts that cross module boundaries.
- Define data models as `pydantic.BaseModel`, not plain dataclasses,
  for anything that touches the API or storage layer.

---

## 4. Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Files | `snake_case.py` | `output_firewall.py` |
| Classes | `PascalCase` | `SecurityScanner`, `TrustScore` |
| Functions | `snake_case` | `compute_trust_score()` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_TRUST_THRESHOLD` |
| Pydantic models | `PascalCase` + noun | `IngestRequest`, `QueryResponse` |
| Type aliases | `PascalCase` | `ChunkText = str` |
| Private helpers | `_leading_underscore` | `_normalize_url()` |
| Test functions | `test_<what>_<condition>` | `test_scanner_catches_injection_pattern` |

---

## 5. Docstrings

All public functions, classes, and modules require docstrings.

```python
def compute_trust_score(text: str, url_allowlist: list[str]) -> float:
    """
    Compute a trust score for a document chunk.

    Score ranges from 0.0 (fully untrusted) to 1.0 (fully trusted).
    Scores below settings.trust_threshold route to quarantine.

    Args:
        text: Raw chunk text after normalization.
        url_allowlist: Domains considered safe for URL presence.

    Returns:
        Float in [0.0, 1.0].

    Raises:
        ValueError: If text is empty.
    """
```

Private helper functions need at minimum a one-line docstring.

---

## 6. Error Handling

```python
# ✅ Catch specific exceptions; log with context; re-raise or return typed error
try:
    result = load_pdf(path)
except FileNotFoundError:
    logger.error("document_not_found", path=str(path))
    raise DocumentLoadError(f"File not found: {path}") from None

# ❌ Never do these
except Exception:          # Too broad
    pass                   # Silent failure
except Exception as e:
    print(e)               # Use structlog, not print
```

- Define custom exceptions in `app/exceptions.py` (one file).
- All custom exceptions inherit from a base `SecureRAGError`.
- HTTP exceptions in `api/` use FastAPI's `HTTPException` with detail dicts:
  ```python
  raise HTTPException(status_code=400, detail={"error": "invalid_file_type", "allowed": ["pdf", "md", "txt"]})
  ```

---

## 7. Security-Specific Code Standards

### Input Validation

```python
# ✅ Validate before any processing
class IngestRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    filename: str = Field(..., max_length=255, pattern=r'^[\w\-. ]+$')
    content_type: Literal["application/pdf", "text/markdown", "text/plain"]

# ❌ Never process raw request data without a Pydantic model
```

### Regex Patterns

All regex patterns used for security scanning live in `security/patterns.py`:

```python
# security/patterns.py
INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+(a\s+)?.*\s+AI', re.IGNORECASE),
    # ... add new patterns here, with a comment for each
]
```

Never define security regex inline in scanner functions.

### Logging Sensitive Data

```python
# ✅ Log metadata only
logger.info("chunk_scanned", doc_id=doc_id, chunk_index=i, trust_score=score)

# ❌ Never log raw content at INFO+
logger.info("chunk_text", text=chunk_text)      # Forbidden at INFO
logger.debug("chunk_text", text=chunk_text)     # OK at DEBUG, gated by LOG_LEVEL
```

---

## 8. Testing Standards

### Unit Test Template

```python
# tests/unit/test_<module>.py
"""Unit tests for app/<layer>/<module>.py"""
import pytest
from app.<layer>.<module> import <FunctionOrClass>


class Test<ClassName>:
    """Tests for <ClassName>."""

    def test_<scenario>_<expected_outcome>(self) -> None:
        """<One-line description of what this test verifies>."""
        # Arrange
        ...
        # Act
        result = <function>(...)
        # Assert
        assert result == expected
```

### Security Test Requirements

Every security function needs **at minimum**:
- 3 cases that MUST trigger the security check (true positives)
- 3 cases that MUST NOT trigger (true negatives / no false positives)
- 1 edge case (empty input, unicode, very long string)

### Test File Mapping

| Module | Test File |
|--------|-----------|
| `security/scanner.py` | `tests/unit/test_scanner.py` |
| `security/output_firewall.py` | `tests/unit/test_output_firewall.py` |
| `ingestion/loader.py` | `tests/unit/test_loader.py` |
| `ingestion/chunker.py` | `tests/unit/test_chunker.py` |
| `retrieval/retriever.py` | `tests/unit/test_retriever.py` |
| `generation/prompt_builder.py` | `tests/unit/test_prompt_builder.py` |

---

## 9. Import Order

Follow `isort` order (enforced in CI):

```python
# 1. Standard library
import re
import hashlib
from pathlib import Path

# 2. Third-party
import structlog
from pydantic import BaseModel

# 3. Internal — absolute imports only
from app.config import get_settings
from app.security.patterns import INJECTION_PATTERNS
```

No relative imports (no `from . import ...`). All imports are absolute.

---

## 10. Function Length Limit

**40 lines maximum** per function (excluding docstring and blank lines).

If a function exceeds 40 lines:
1. Identify the sub-operations inside it.
2. Extract each into a private helper (`_name()`).
3. The public function becomes an orchestrator of helpers.

```python
# ✅ Orchestrator pattern for long logic
def scan_document(text: str) -> ScanResult:
    """Run all security checks on a document chunk."""
    injection_flags = _check_injection_patterns(text)
    url_flags = _check_urls(text, get_settings().url_allowlist)
    entropy_flag = _check_entropy_anomaly(text)
    return _build_scan_result(injection_flags, url_flags, entropy_flag)
```

---

## 11. Configuration Access

Always use the settings singleton. Never hardcode values.

```python
# ✅ Correct
from app.config import get_settings
settings = get_settings()
if score < settings.trust_threshold:
    ...

# ❌ Wrong
if score < 0.7:    # Hardcoded — breaks when env changes
    ...
```

---

## 12. Commit & PR Standards

- One logical change per commit.
- Commit message format: `type(scope): description`
  - `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `security`
- PR description must include: what changed, why, how to test it.
- Every PR must have passing `pytest tests/unit/` before review.
- Security-related PRs must also pass `pytest tests/redteam/`.

---

*Last updated: 2025-05-15 | Standards Owner: Team | Agent: Antigravity*
