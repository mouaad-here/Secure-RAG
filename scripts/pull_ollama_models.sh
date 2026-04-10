#!/bin/bash
# =============================================================================
# Pull required Ollama models
# Run inside the Ollama container: docker exec rag-ollama bash /app/scripts/pull_ollama_models.sh
# Or from host: docker exec rag-ollama ollama pull llama3.2:3b
# =============================================================================

set -e

echo "🔄 Pulling LLM model: llama3.2:3b ..."
ollama pull llama3.2:3b

echo "🔄 Pulling embedding model: nomic-embed-text ..."
ollama pull nomic-embed-text

echo "✅ All models pulled successfully!"
echo ""
echo "📋 Installed models:"
ollama list
