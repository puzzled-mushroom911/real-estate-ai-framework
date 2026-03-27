#!/usr/bin/env bash
# ============================================================
# Real Estate Agent AI Framework - Setup Script
# ============================================================
# Usage: bash scripts/setup.sh
# This script installs all dependencies and configures the framework.

set -e

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$HOME/.real_estate_ai"

echo "============================================================"
echo "  Real Estate Agent AI Framework - Setup"
echo "============================================================"
echo ""
echo "Framework directory: $FRAMEWORK_DIR"
echo ""

# --- Step 1: Check prerequisites ---
echo "[1/7] Checking prerequisites..."

check_command() {
    if command -v "$1" &>/dev/null; then
        echo "  OK: $1 found ($(command -v "$1"))"
        return 0
    else
        echo "  MISSING: $1 not found"
        return 1
    fi
}

MISSING=0
check_command python3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command yt-dlp || { echo "  Install with: brew install yt-dlp (or pip install yt-dlp)"; MISSING=1; }

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "ERROR: Missing prerequisites. Install them and re-run this script."
    exit 1
fi

# Check Python version
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python version: $PYVER"
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "  OK: Python 3.10+ confirmed"
else
    echo "  ERROR: Python 3.10+ required (found $PYVER)"
    exit 1
fi

# --- Step 2: Create config directory ---
echo ""
echo "[2/7] Creating config directory at $CONFIG_DIR..."
mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/manifest.json" ]; then
    echo '{"datasets": {}, "created": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > "$CONFIG_DIR/manifest.json"
    echo "  Created manifest.json"
fi

# --- Step 3: Install Python dependencies ---
echo ""
echo "[3/7] Installing Python dependencies..."
pip3 install --quiet \
    chromadb \
    sentence-transformers \
    langchain \
    langchain-community \
    langchain-chroma \
    langchain-huggingface \
    langchain-text-splitters \
    python-docx \
    pdfplumber \
    pyyaml \
    requests 2>&1 | tail -3

echo "  Python packages installed"

# --- Step 4: Install MCP server dependencies ---
echo ""
echo "[4/7] Installing MCP server dependencies..."
cd "$FRAMEWORK_DIR/mcp_server"
npm install --silent 2>&1 | tail -3
echo "  Node packages installed"

# --- Step 5: Build MCP server ---
echo ""
echo "[5/7] Building MCP server..."
npm run build 2>&1 | tail -3
echo "  MCP server built"
cd "$FRAMEWORK_DIR"

# --- Step 6: Download embedding model ---
echo ""
echo "[6/7] Pre-downloading embedding model (first-time only)..."
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('  Model downloaded and cached')
" 2>/dev/null || echo "  Model will download on first use"

# --- Step 7: Create .env if missing ---
echo ""
echo "[7/7] Checking configuration..."
if [ ! -f "$FRAMEWORK_DIR/config/.env" ]; then
    cp "$FRAMEWORK_DIR/config/.env.example" "$FRAMEWORK_DIR/config/.env"
    echo "  Created config/.env from template"
    echo "  >>> IMPORTANT: Edit config/.env with your credentials <<<"
else
    echo "  config/.env already exists"
fi

if [ ! -f "$FRAMEWORK_DIR/config/agent_profile.yaml" ]; then
    echo "  >>> IMPORTANT: Edit config/agent_profile.yaml with your info <<<"
fi

# --- Summary ---
echo ""
echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Edit config/agent_profile.yaml with your agent info"
echo "  2. Edit config/.env with your API keys"
echo "  3. Edit config/channels.yaml with your YouTube channels"
echo ""
echo "Quick start:"
echo "  # Ingest your YouTube channel"
echo "  bash scripts/ingest-channel.sh @YourHandle"
echo ""
echo "  # Or use Claude Code with the MCP server"
echo "  # Add to your .mcp.json:"
echo "  {\"mcpServers\": {\"real-estate-agent\": {"
echo "    \"command\": \"node\","
echo "    \"args\": [\"$FRAMEWORK_DIR/mcp_server/dist/index.js\"]"
echo "  }}}"
echo ""
