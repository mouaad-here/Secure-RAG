#!/bin/bash
# =============================================================================
# Seed sample documents into the RAG system
# Run from host: docker exec rag-api bash /app/scripts/seed_sample_docs.sh
# =============================================================================

set -e

API_URL="http://localhost:8000/api/v1"

echo "📄 Seeding sample documents..."

for file in /app/sample_docs/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  → Uploading: $filename"
        curl -s -X POST "$API_URL/ingest" \
            -F "file=@$file" \
            -F "source_label=sample_corpus" \
            | python -m json.tool
        echo ""
    fi
done

echo "✅ Sample documents seeded!"
