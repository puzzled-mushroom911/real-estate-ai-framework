#!/usr/bin/env python3
"""
Import customer conversation history (SMS/email threads) into ChromaDB for
style analysis and RAG retrieval.

Creates two document types per contact:
  1. Full conversation thread (for context retrieval)
  2. Communication style summary (for tone matching)

CSV expected format:
    contact_id, first_name, last_name, lead_score, conversation_text, message_count

Conversation text format (pipe-separated messages):
    2024-01-15 10:30 IN: Hey, interested in homes | 2024-01-15 11:00 OUT: Great! ...

Usage:
    python3 import_conversations.py <conversations.csv> --db-name "my_conversations" [options]

Examples:
    python3 import_conversations.py convos.csv --db-name agent_convos
    python3 import_conversations.py convos.csv --db-name agent_convos --db-dir ./kb
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DB_DIR = "./knowledge_bases/vectors"

# Regex to parse individual messages from conversation_text
# Format: "2024-01-15 10:30 IN: message text" or "2024-01-15 10:30 OUT: message text"
MESSAGE_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(IN|OUT):\s*(.*?)(?=\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+(?:IN|OUT):|$)",
    re.DOTALL,
)

# RAG system manager registry path
RAG_REGISTRY_PATH = Path.home() / ".real_estate_ai" / "rag_registry.json"


# ---------------------------------------------------------------------------
# Message parsing
# ---------------------------------------------------------------------------
def parse_conversation(raw_text: str) -> List[Dict[str, str]]:
    """
    Parse a conversation text blob into structured messages.

    Handles both pipe-separated and newline-separated formats.

    Args:
        raw_text: The raw conversation_text field from the CSV.

    Returns:
        List of dicts with keys: timestamp, direction, text.
    """
    if not raw_text or not raw_text.strip():
        return []

    # Normalize pipe separators to newlines for uniform parsing
    normalized = raw_text.replace(" | ", "\n").replace("|", "\n")

    messages: List[Dict[str, str]] = []
    for match in MESSAGE_PATTERN.finditer(normalized):
        timestamp_str, direction, text = match.groups()
        messages.append({
            "timestamp": timestamp_str.strip(),
            "direction": direction.strip(),  # IN = from contact, OUT = from agent
            "text": text.strip(),
        })

    # Fallback: if regex found nothing, treat the whole blob as a single message
    if not messages and raw_text.strip():
        messages.append({
            "timestamp": "",
            "direction": "UNKNOWN",
            "text": raw_text.strip(),
        })

    return messages


def build_thread_text(messages: List[Dict[str, str]], contact_name: str) -> str:
    """Format parsed messages into a readable conversation thread."""
    lines = [f"Conversation with {contact_name}:", ""]
    for msg in messages:
        speaker = contact_name if msg["direction"] == "IN" else "Agent"
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{speaker}: {msg['text']}")
    return "\n".join(lines)


def analyze_style(messages: List[Dict[str, str]], contact_name: str) -> str:
    """
    Generate a communication style summary from parsed messages.

    Extracts: message lengths, formality signals, question frequency,
    response patterns, and topic indicators.
    """
    in_msgs = [m for m in messages if m["direction"] == "IN"]
    out_msgs = [m for m in messages if m["direction"] == "OUT"]

    if not in_msgs and not out_msgs:
        return f"No analyzable messages for {contact_name}."

    # Analyze contact's messages (IN)
    in_lengths = [len(m["text"].split()) for m in in_msgs] if in_msgs else [0]
    avg_in_len = sum(in_lengths) / max(len(in_lengths), 1)
    in_questions = sum(1 for m in in_msgs if "?" in m["text"])
    in_exclamations = sum(1 for m in in_msgs if "!" in m["text"])

    # Analyze agent's messages (OUT)
    out_lengths = [len(m["text"].split()) for m in out_msgs] if out_msgs else [0]
    avg_out_len = sum(out_lengths) / max(len(out_lengths), 1)

    # Formality heuristics
    casual_markers = {"hey", "yeah", "lol", "haha", "gonna", "wanna", "thx", "ty"}
    formal_markers = {"regarding", "furthermore", "appreciate", "sincerely", "respectfully"}
    all_in_words = {w.lower().strip(".,!?") for m in in_msgs for w in m["text"].split()}
    casual_count = len(all_in_words & casual_markers)
    formal_count = len(all_in_words & formal_markers)

    if casual_count > formal_count:
        tone = "casual/informal"
    elif formal_count > casual_count:
        tone = "formal/professional"
    else:
        tone = "neutral/mixed"

    summary_lines = [
        f"Communication Style Summary for {contact_name}:",
        f"  Total messages: {len(messages)} ({len(in_msgs)} from contact, {len(out_msgs)} from agent)",
        f"  Contact avg message length: {avg_in_len:.0f} words",
        f"  Agent avg message length: {avg_out_len:.0f} words",
        f"  Contact questions asked: {in_questions}",
        f"  Detected tone: {tone}",
        f"  Enthusiasm signals (exclamations): {in_exclamations}",
    ]

    # Detect common real estate topics
    topic_keywords = {
        "pricing": {"price", "cost", "budget", "afford", "expensive", "cheap"},
        "location": {"neighborhood", "area", "location", "commute", "school", "district"},
        "property_type": {"condo", "house", "townhouse", "apartment", "single-family", "duplex"},
        "timeline": {"soon", "asap", "month", "year", "timeline", "when", "ready"},
        "financing": {"mortgage", "loan", "pre-approved", "down payment", "interest rate"},
    }

    all_text_lower = " ".join(m["text"].lower() for m in in_msgs)
    detected_topics = []
    for topic, keywords in topic_keywords.items():
        if any(kw in all_text_lower for kw in keywords):
            detected_topics.append(topic)

    if detected_topics:
        summary_lines.append(f"  Topics discussed: {', '.join(detected_topics)}")

    return "\n".join(summary_lines)


# ---------------------------------------------------------------------------
# ChromaDB storage
# ---------------------------------------------------------------------------
def create_documents(rows: List[Dict[str, str]]) -> Tuple[List[Document], List[Document]]:
    """
    Build LangChain Document objects from parsed CSV rows.

    Returns:
        Tuple of (thread_documents, style_documents).
    """
    thread_docs: List[Document] = []
    style_docs: List[Document] = []

    for row in rows:
        contact_id = row.get("contact_id", "unknown")
        first_name = row.get("first_name", "").strip()
        last_name = row.get("last_name", "").strip()
        contact_name = f"{first_name} {last_name}".strip() or f"Contact {contact_id}"
        lead_score = row.get("lead_score", "")
        message_count = row.get("message_count", "0")
        raw_convo = row.get("conversation_text", "")

        messages = parse_conversation(raw_convo)
        if not messages:
            continue

        metadata = {
            "contact_id": contact_id,
            "contact_name": contact_name,
            "lead_score": lead_score,
            "message_count": message_count,
            "source": f"conversation_{contact_id}",
        }

        # Document type 1: Full conversation thread
        thread_text = build_thread_text(messages, contact_name)
        thread_docs.append(Document(
            page_content=thread_text,
            metadata={**metadata, "doc_type": "conversation_thread"},
        ))

        # Document type 2: Communication style summary
        style_text = analyze_style(messages, contact_name)
        style_docs.append(Document(
            page_content=style_text,
            metadata={**metadata, "doc_type": "communication_style"},
        ))

    return thread_docs, style_docs


def store_in_chromadb(
    documents: List[Document],
    db_dir: Path,
    db_name: str,
) -> int:
    """
    Embed and store documents in a ChromaDB collection.

    Args:
        documents: List of LangChain Documents to store.
        db_dir: Parent directory for the vector database.
        db_name: Name for the ChromaDB collection.

    Returns:
        Number of documents stored.
    """
    db_path = db_dir / db_name
    db_path.mkdir(parents=True, exist_ok=True)

    print(f"Loading embedding model ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=str(db_path))
    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        client=client,
        collection_name=db_name,
    )

    return len(documents)


def register_in_rag_system(db_name: str, db_dir: Path, doc_count: int) -> None:
    """Register the new knowledge base in the RAG system manager registry."""
    RAG_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    registry: Dict[str, Any] = {}
    if RAG_REGISTRY_PATH.exists():
        try:
            registry = json.loads(RAG_REGISTRY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            registry = {}

    registry[db_name] = {
        "path": str(db_dir / db_name),
        "collection": db_name,
        "documents": doc_count,
        "type": "conversation_history",
        "created": datetime.now().isoformat(),
    }

    RAG_REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"Registered '{db_name}' in RAG registry at {RAG_REGISTRY_PATH}")


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------
def import_conversations(
    csv_path: Path,
    db_name: str,
    db_dir: Path,
) -> Dict[str, int]:
    """
    Full pipeline: read CSV -> parse -> create documents -> embed -> store.

    Args:
        csv_path: Path to the conversations CSV.
        db_name: Name for the ChromaDB collection/database.
        db_dir: Parent directory for vector databases.

    Returns:
        Dict with import statistics.
    """
    print("=" * 80)
    print("Conversation History Importer")
    print("=" * 80)
    print(f"  Source CSV    : {csv_path}")
    print(f"  Database name : {db_name}")
    print(f"  Database dir  : {db_dir}")
    print("=" * 80)

    # Read CSV
    print("\nReading conversations...")
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"  Found {len(rows)} contact records")

    # Parse and create documents
    print("\nParsing conversations and generating documents...")
    thread_docs, style_docs = create_documents(rows)
    all_docs = thread_docs + style_docs
    print(f"  Created {len(thread_docs)} conversation thread documents")
    print(f"  Created {len(style_docs)} communication style documents")
    print(f"  Total documents: {len(all_docs)}")

    if not all_docs:
        print("\nWarning: no valid conversations found in the CSV.")
        return {"total_rows": len(rows), "thread_docs": 0, "style_docs": 0, "stored": 0}

    # Store in ChromaDB
    print(f"\nEmbedding and storing in ChromaDB ({db_name})...")
    stored = store_in_chromadb(all_docs, db_dir, db_name)

    # Register
    register_in_rag_system(db_name, db_dir, stored)

    stats = {
        "total_rows": len(rows),
        "thread_docs": len(thread_docs),
        "style_docs": len(style_docs),
        "stored": stored,
    }

    print("\n" + "=" * 80)
    print("IMPORT COMPLETE")
    print("=" * 80)
    print(f"  Contact records processed : {stats['total_rows']}")
    print(f"  Thread documents created  : {stats['thread_docs']}")
    print(f"  Style documents created   : {stats['style_docs']}")
    print(f"  Total documents stored    : {stats['stored']}")
    print(f"\nQuery with:")
    print(f'  python3 rag_query.py "communication style" --db-path {db_dir / db_name}')
    print("=" * 80)

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import conversation history into ChromaDB for RAG retrieval.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Expected CSV columns:\n"
            "  contact_id, first_name, last_name, lead_score, conversation_text, message_count\n\n"
            "Conversation text format (pipe-separated):\n"
            '  "2024-01-15 10:30 IN: Hi! | 2024-01-15 11:00 OUT: Welcome!"\n\n'
            "Examples:\n"
            '  python3 import_conversations.py convos.csv --db-name agent_convos\n'
            '  python3 import_conversations.py convos.csv --db-name agent_convos --db-dir ./kb\n'
        ),
    )
    parser.add_argument("conversations_csv", help="Path to the conversations CSV file")
    parser.add_argument(
        "--db-name",
        required=True,
        help="Name for the ChromaDB collection/database",
    )
    parser.add_argument(
        "--db-dir",
        default=DEFAULT_DB_DIR,
        help=f"Parent directory for vector databases (default: {DEFAULT_DB_DIR})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    csv_path = Path(args.conversations_csv)
    if not csv_path.exists():
        print(f"Error: file '{csv_path}' does not exist.")
        sys.exit(1)

    db_dir = Path(args.db_dir).resolve()

    import_conversations(
        csv_path=csv_path,
        db_name=args.db_name,
        db_dir=db_dir,
    )
