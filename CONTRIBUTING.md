# Contributing to Secure RAG MVP

Thank you for contributing! This guide will help you get started.

## 🚀 Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/mouaad-here/Secure-RAG.git
   cd Secure-RAG
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   docker compose up -d
   ```

3. **Pull models (first time):**
   ```bash
   docker exec rag-ollama ollama pull llama3.2:3b
   docker exec rag-ollama ollama pull nomic-embed-text
   ```

4. **Verify:**
   ```bash
   curl http://localhost:8000/health
   ```

## 🌿 Branch Workflow

1. Always branch from `integration/mvp`:
   ```bash
   git checkout integration/mvp && git pull
   git checkout -b feature/my-feature
   ```

2. Make focused commits using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(scope): description
   fix(scope): description
   docs(scope): description
   test(scope): description
   refactor(scope): description
   ```

3. Push and open a PR targeting `integration/mvp`:
   ```bash
   git push -u origin feature/my-feature
   ```

## ✅ Before Submitting a PR

- [ ] All existing tests pass: `docker compose exec api pytest`
- [ ] New features include unit tests
- [ ] Code follows project style (checked by `ruff`)
- [ ] Documentation updated if needed

## 🧪 Running Tests

```bash
# All tests
docker compose exec api pytest

# Specific test file
docker compose exec api pytest tests/unit/test_scanner.py -v

# With coverage
docker compose exec api pytest --cov=app
```

## 📁 Code Organization

- **One module per concern** — don't mix responsibilities
- **Type hints everywhere** — makes code self-documenting
- **Docstrings on all public classes/methods**
- **Security-first** — always consider attack vectors

## 🔒 Security Guidelines

- Never commit `.env` files
- Never commit data from the `data/` directory
- Test all new features against red-team documents
- Document any security assumptions
