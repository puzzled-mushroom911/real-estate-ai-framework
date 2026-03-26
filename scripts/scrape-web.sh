#!/usr/bin/env bash
# ============================================================
# Scrape a Website into the Knowledge Base
# ============================================================
# Usage: bash scripts/scrape-web.sh https://www.yourwebsite.com [--depth 2]
#
# Downloads page content and indexes it for search.
# For Google reviews, use Claude in Chrome instead.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$FRAMEWORK_DIR/tools"
KB_DIR="$FRAMEWORK_DIR/knowledge_bases"
OUTPUT_DIR="$KB_DIR/transcripts/web"

URL="${1:?Usage: bash scripts/scrape-web.sh https://www.yourwebsite.com [--depth 2]}"
DEPTH="${3:-1}"

mkdir -p "$OUTPUT_DIR"

# Derive a safe filename from the URL
SAFE_NAME=$(echo "$URL" | sed 's|https\?://||;s|[^a-zA-Z0-9]|_|g' | cut -c1-60)

echo "============================================================"
echo "  Scraping: $URL"
echo "  Output: $OUTPUT_DIR/${SAFE_NAME}.txt"
echo "============================================================"
echo ""

# Use curl to fetch the page content, strip HTML tags
echo "[1/2] Downloading page content..."
curl -sL "$URL" \
  | python3 -c "
import sys, re, html
text = sys.stdin.read()
# Remove script and style blocks
text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL|re.IGNORECASE)
# Remove HTML tags
text = re.sub(r'<[^>]+>', '\n', text)
# Decode HTML entities
text = html.unescape(text)
# Clean up whitespace
text = re.sub(r'\n\s*\n', '\n\n', text).strip()
print(text)
" > "$OUTPUT_DIR/${SAFE_NAME}.txt"

FILESIZE=$(wc -c < "$OUTPUT_DIR/${SAFE_NAME}.txt" | tr -d ' ')
echo "  Downloaded: ${FILESIZE} bytes"

if [ "$FILESIZE" -lt 100 ]; then
  echo "  WARNING: Very little content extracted. The site may require JavaScript."
  echo "  Try using Claude in Chrome for JavaScript-heavy sites."
fi

# Step 2: Index into knowledge base
echo ""
echo "[2/2] Indexing into knowledge base..."
python3 "$TOOLS_DIR/rag_tools/create_knowledge_base.py" \
  "$OUTPUT_DIR/${SAFE_NAME}.txt" \
  --db-dir "$KB_DIR/vectors/web_content" \
  --collection-name "web_content"

echo ""
echo "============================================================"
echo "  Done! Website content indexed as: web_content"
echo "============================================================"
echo ""
echo "Test it:"
echo "  python3 $TOOLS_DIR/rag_tools/rag_query.py \"about us\" --db-path $KB_DIR/vectors/web_content"
