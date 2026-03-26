#!/usr/bin/env bash
# ============================================================
# Ingest a YouTube Channel into the Knowledge Base
# ============================================================
# Usage: bash scripts/ingest-channel.sh @ChannelHandle [--days 60] [--max 50]
#
# This script downloads transcripts and ingests them into ChromaDB.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$FRAMEWORK_DIR/tools"
KB_DIR="$FRAMEWORK_DIR/knowledge_bases"
TRANSCRIPT_DIR="$KB_DIR/transcripts"

CHANNEL_HANDLE="${1:?Usage: bash scripts/ingest-channel.sh @ChannelHandle [--days 60] [--max 50]}"
DAYS="${2:---days}"
DAYS_VAL="${3:-60}"
MAX="${4:---max}"
MAX_VAL="${5:-50}"

# Derive db name from handle (strip @ and lowercase)
DB_NAME="youtube_$(echo "$CHANNEL_HANDLE" | sed 's/@//' | tr '[:upper:]' '[:lower:]' | tr '-' '_')"

echo "============================================================"
echo "  Ingesting YouTube Channel: $CHANNEL_HANDLE"
echo "  Database name: $DB_NAME"
echo "============================================================"
echo ""

# Step 1: Fetch videos and transcripts
echo "[1/2] Fetching videos and transcripts..."
python3 "$TOOLS_DIR/youtube_tools/fetch_videos.py" \
    --channel "$CHANNEL_HANDLE" \
    --days "$DAYS_VAL" \
    --max "$MAX_VAL" \
    --output-dir "$TRANSCRIPT_DIR"

# Find the output directory for this channel
CHANNEL_DIR=$(find "$TRANSCRIPT_DIR" -maxdepth 1 -type d -name "*$(echo "$CHANNEL_HANDLE" | sed 's/@//')*" | head -1)

if [ -z "$CHANNEL_DIR" ]; then
    # Fallback: use the channel handle as directory name
    CHANNEL_DIR="$TRANSCRIPT_DIR/$(echo "$CHANNEL_HANDLE" | sed 's/@//')"
fi

if [ ! -d "$CHANNEL_DIR" ] || [ -z "$(ls -A "$CHANNEL_DIR"/*.txt 2>/dev/null)" ]; then
    echo "ERROR: No transcripts found in $CHANNEL_DIR"
    echo "Check that yt-dlp can access the channel and that videos have captions."
    exit 1
fi

# Step 2: Ingest to RAG
echo ""
echo "[2/2] Ingesting transcripts to ChromaDB..."
python3 "$TOOLS_DIR/youtube_tools/ingest_to_rag.py" \
    "$CHANNEL_DIR" \
    --db-name "$DB_NAME" \
    --db-dir "$KB_DIR/vectors"

echo ""
echo "============================================================"
echo "  Done! Channel ingested as: $DB_NAME"
echo "============================================================"
echo ""
echo "Test it:"
echo "  python3 $TOOLS_DIR/rag_tools/rag_query.py \"best neighborhoods\" --db-path $KB_DIR/vectors/$DB_NAME"
echo ""
