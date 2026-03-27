#!/usr/bin/env bash
# ============================================================
# Ingest Content into the Knowledge Base
# ============================================================
# Usage:
#   bash scripts/ingest-content.sh youtube @ChannelHandle
#   bash scripts/ingest-content.sh documents [path]
#   bash scripts/ingest-content.sh csv [file.csv] [--type sales|leads|contacts]
#   bash scripts/ingest-content.sh audio [path-to-audio-files]
#
# This is a unified entry point for all content ingestion.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$FRAMEWORK_DIR/tools"
KB_DIR="$FRAMEWORK_DIR/knowledge_bases"
MY_DATA="$FRAMEWORK_DIR/my_data"

SOURCE_TYPE="${1:?Usage: bash scripts/ingest-content.sh <youtube|documents|csv|audio> [args...]}"
shift

case "$SOURCE_TYPE" in
  youtube)
    CHANNEL="${1:?Provide a YouTube channel handle, e.g., @YourChannel}"
    echo "Ingesting YouTube channel: $CHANNEL"
    bash "$FRAMEWORK_DIR/scripts/ingest-channel.sh" "$CHANNEL" "${@:2}"
    ;;

  documents)
    DOC_DIR="${1:-$MY_DATA/documents}"
    if [ ! -d "$DOC_DIR" ] || [ -z "$(ls -A "$DOC_DIR" 2>/dev/null | grep -v .gitkeep)" ]; then
      echo "No documents found in $DOC_DIR"
      echo "Drop .md, .txt, .pdf, or .docx files there and re-run."
      exit 1
    fi
    echo "Indexing documents from: $DOC_DIR"
    python3 "$TOOLS_DIR/rag_tools/create_knowledge_base.py" \
      "$DOC_DIR" \
      --db-dir "$KB_DIR/vectors/local_documents" \
      --collection-name "local_documents"
    echo "Documents indexed successfully."
    ;;

  csv)
    CSV_FILE="${1:?Provide a CSV file path}"
    CSV_TYPE="${3:-contacts}"
    if [ ! -f "$CSV_FILE" ]; then
      echo "File not found: $CSV_FILE"
      exit 1
    fi
    echo "Processing CSV ($CSV_TYPE): $CSV_FILE"
    python3 "$TOOLS_DIR/csv_tools/process_contacts.py" "$CSV_FILE" --type "$CSV_TYPE"
    echo "CSV processed successfully."
    ;;

  audio)
    AUDIO_DIR="${1:-$MY_DATA/podcasts}"
    if [ ! -d "$AUDIO_DIR" ] || [ -z "$(ls -A "$AUDIO_DIR" 2>/dev/null | grep -v .gitkeep)" ]; then
      echo "No audio files found in $AUDIO_DIR"
      echo "Drop .mp3, .m4a, or .wav files there and re-run."
      exit 1
    fi
    echo "Extracting and indexing audio from: $AUDIO_DIR"
    # Convert audio to text transcripts, then index
    TRANSCRIPT_DIR="$KB_DIR/transcripts/audio"
    mkdir -p "$TRANSCRIPT_DIR"

    for file in "$AUDIO_DIR"/*.{mp3,m4a,wav,mp4} 2>/dev/null; do
      [ -f "$file" ] || continue
      BASENAME=$(basename "$file" | sed 's/\.[^.]*$//')
      echo "  Processing: $(basename "$file")"
      # Extract audio if video, then transcribe
      if [[ "$file" == *.mp4 ]]; then
        ffmpeg -i "$file" -vn -acodec libmp3lame -q:a 2 "$TRANSCRIPT_DIR/${BASENAME}.mp3" -y 2>/dev/null
      fi
    done

    echo ""
    echo "Audio files prepared in: $TRANSCRIPT_DIR"
    echo "Use Claude to transcribe and index these files."
    ;;

  *)
    echo "Unknown source type: $SOURCE_TYPE"
    echo ""
    echo "Usage:"
    echo "  bash scripts/ingest-content.sh youtube @ChannelHandle"
    echo "  bash scripts/ingest-content.sh documents [path]"
    echo "  bash scripts/ingest-content.sh csv file.csv [--type sales|leads|contacts]"
    echo "  bash scripts/ingest-content.sh audio [path]"
    exit 1
    ;;
esac
