#!/usr/bin/env python3
"""
Query a single ChromaDB vector database with semantic search.

Auto-detects the collection name from the database and returns results
with content, source metadata, and relevance scores.

Usage:
    python3 rag_query.py "your question" [options]

Examples:
    python3 rag_query.py "What neighborhoods are best for families?"
    python3 rag_query.py "market trends" --db-path ./market_kb --k 10
    python3 rag_query.py "school ratings" --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------
def query_knowledge_base(
    question: str,
    db_path: str = "./kb",
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Run a semantic search against a ChromaDB knowledge base.

    Args:
        question: Natural-language query string.
        db_path: Path to the ChromaDB persistent directory.
        k: Number of results to return.

    Returns:
        List of dicts with keys: rank, score, source, content, metadata.
    """
    db_resolved = Path(db_path).resolve()

    if not db_resolved.exists():
        print(f"Error: database directory '{db_resolved}' does not exist.")
        print("Create one first with: python3 create_knowledge_base.py <source_dir>")
        sys.exit(1)

    # Auto-detect collection name from the database
    client = chromadb.PersistentClient(path=str(db_resolved))
    collections = client.list_collections()
    if not collections:
        print(f"Error: no collections found in '{db_resolved}'.")
        sys.exit(1)
    collection_name = collections[0].name

    # Load embeddings and vector store
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    # Perform similarity search
    raw_results = vectorstore.similarity_search_with_score(question, k=k)

    results: List[Dict[str, Any]] = []
    for rank, (doc, score) in enumerate(raw_results, start=1):
        results.append({
            "rank": rank,
            "score": round(float(score), 4),
            "source": doc.metadata.get("source", "unknown"),
            "content": doc.page_content,
            "metadata": doc.metadata,
        })

    return results


def format_results_text(results: List[Dict[str, Any]], question: str) -> str:
    """Format query results as human-readable text."""
    if not results:
        return "No results found."

    lines = [
        f"Found {len(results)} result(s) for: {question}",
        "=" * 80,
    ]
    for r in results:
        lines.append(f"\n--- Result {r['rank']} (score: {r['score']}) ---")
        lines.append(f"Source: {r['source']}")
        lines.append(f"\n{r['content']}\n")
        lines.append("-" * 80)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query a ChromaDB vector database with semantic search.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python3 rag_query.py "best neighborhoods"\n'
            '  python3 rag_query.py "market trends" --db-path ./market_kb --k 10\n'
            '  python3 rag_query.py "school ratings" --json\n'
        ),
    )
    parser.add_argument("query", help="Natural-language search query")
    parser.add_argument(
        "--db-path",
        default="./kb",
        help="Path to the ChromaDB database directory (default: ./kb)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of formatted text",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    results = query_knowledge_base(
        question=args.query,
        db_path=args.db_path,
        k=args.k,
    )

    if args.json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_results_text(results, args.query))
