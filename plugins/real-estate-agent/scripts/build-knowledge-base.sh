#!/usr/bin/env bash
# ============================================================
# Build All Knowledge Bases
# ============================================================
# Usage: bash scripts/build-knowledge-base.sh
#
# Reads config/channels.yaml and ingests all configured channels.
# Also indexes any documents in knowledge_bases/documents/.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$FRAMEWORK_DIR/tools"
KB_DIR="$FRAMEWORK_DIR/knowledge_bases"

echo "============================================================"
echo "  Building All Knowledge Bases"
echo "============================================================"
echo ""

# Check for channels config
CHANNELS_FILE="$FRAMEWORK_DIR/config/channels.yaml"
if [ ! -f "$CHANNELS_FILE" ]; then
    echo "ERROR: config/channels.yaml not found. Copy from the template and configure your channels."
    exit 1
fi

# Extract channel handles from YAML (simple grep approach)
echo "[1/3] Ingesting YouTube channels from config/channels.yaml..."
echo ""

HANDLES=$(python3 -c "
import yaml
from pathlib import Path
data = yaml.safe_load(Path('$CHANNELS_FILE').read_text())
for ch in data.get('channels', []):
    print(ch['handle'])
" 2>/dev/null)

if [ -z "$HANDLES" ]; then
    echo "  No channels configured in channels.yaml"
else
    while IFS= read -r handle; do
        echo "--- Ingesting: $handle ---"
        bash "$FRAMEWORK_DIR/scripts/ingest-channel.sh" "$handle" --days 90 --max 100
        echo ""
    done <<< "$HANDLES"
fi

# Index any local documents
echo "[2/3] Indexing local documents..."
DOC_DIR="$KB_DIR/documents"
if [ -d "$DOC_DIR" ] && [ "$(ls -A "$DOC_DIR" 2>/dev/null)" ]; then
    python3 "$TOOLS_DIR/rag_tools/create_knowledge_base.py" \
        "$DOC_DIR" \
        --db-dir "$KB_DIR/vectors/local_documents" \
        --collection-name "local_documents"
    echo "  Local documents indexed"
else
    echo "  No documents found in knowledge_bases/documents/ (skipping)"
    echo "  Add .md, .txt, .pdf, or .docx files there to index them."
fi

# List all databases
echo ""
echo "[3/3] Knowledge base inventory:"
python3 "$TOOLS_DIR/rag_tools/rag_system_manager.py" list 2>/dev/null || echo "  (No databases registered yet)"

echo ""
echo "============================================================"
echo "  Knowledge bases built!"
echo "============================================================"
