#!/usr/bin/env python3
"""
Multi-database RAG query interface.

Query one or more ChromaDB vector databases, combine and rank results by
relevance, and include source attribution for each result.

Usage:
    python3 rag_query_multi.py "query" --databases db1,db2 [options]
    python3 rag_query_multi.py "query" --all [options]

Examples:
    python3 rag_query_multi.py "best neighborhoods" --databases market_kb,community_kb
    python3 rag_query_multi.py "school ratings" --all --k 5
    python3 rag_query_multi.py "relocation tips" --all --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from rag_system_manager import RAGSystemManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------
class MultiDatabaseRAG:
    """Query multiple ChromaDB databases and merge results."""

    def __init__(self, manifest_path: str | None = None):
        self.manager = RAGSystemManager(manifest_path=manifest_path)
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    def _query_single(
        self, dataset_name: str, question: str, k: int
    ) -> List[Dict[str, Any]]:
        """Query one registered database and return tagged results."""
        db_path = self.manager.get_dataset_path(dataset_name)
        if not db_path:
            print(f"Warning: dataset '{dataset_name}' not found in registry.")
            return []

        resolved = Path(db_path).resolve()
        if not resolved.exists():
            print(f"Warning: path '{resolved}' does not exist for '{dataset_name}'.")
            return []

        try:
            client = chromadb.PersistentClient(path=str(resolved))
            collections = client.list_collections()
            if not collections:
                print(f"Warning: no collections in '{dataset_name}'.")
                return []

            collection_name = collections[0].name
            vectorstore = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embeddings,
            )
            raw = vectorstore.similarity_search_with_score(question, k=k)

            return [
                {
                    "dataset": dataset_name,
                    "score": round(float(score), 4),
                    "source": doc.metadata.get("source", "unknown"),
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc, score in raw
            ]
        except Exception as exc:
            print(f"Warning: error querying '{dataset_name}': {exc}")
            return []

    def query(
        self,
        dataset_names: List[str],
        question: str,
        k_per_dataset: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Query multiple databases and return combined, relevance-sorted results.

        Args:
            dataset_names: List of registered dataset names to query.
            question: Natural-language query.
            k_per_dataset: Results to retrieve from each database.

        Returns:
            Merged list of result dicts sorted by relevance score (ascending).
        """
        all_results: List[Dict[str, Any]] = []
        for name in dataset_names:
            all_results.extend(self._query_single(name, question, k_per_dataset))

        # Lower score = closer match (cosine distance)
        all_results.sort(key=lambda r: r["score"])
        return all_results

    def query_all(
        self, question: str, k_per_dataset: int = 3
    ) -> List[Dict[str, Any]]:
        """Query every registered dataset."""
        datasets = self.manager.list_datasets()
        names = list(datasets.keys())
        if not names:
            print("No datasets registered. Use rag_system_manager.py to register one.")
            return []
        print(f"Searching across {len(names)} dataset(s): {', '.join(names)}")
        return self.query(names, question, k_per_dataset)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def format_results_text(
    results: List[Dict[str, Any]], question: str, max_results: int | None = None
) -> str:
    """Render results as human-readable text."""
    if not results:
        return "No results found."

    display = results[:max_results] if max_results else results
    lines = [
        f"Found {len(display)} result(s) for: {question}",
        "=" * 80,
    ]
    for i, r in enumerate(display, start=1):
        lines.append(f"\n--- Result {i} (score: {r['score']}) ---")
        lines.append(f"Dataset: {r['dataset']}")
        lines.append(f"Source : {r['source']}")

        # Surface YouTube-specific metadata when present
        meta = r.get("metadata", {})
        if meta.get("source") == "youtube" or meta.get("video_title"):
            lines.append(f"Video  : {meta.get('video_title', 'N/A')}")
            lines.append(f"Channel: {meta.get('channel_name', 'N/A')}")

        lines.append(f"\n{r['content']}\n")
        lines.append("-" * 80)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query multiple ChromaDB databases and combine results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python3 rag_query_multi.py "best neighborhoods" --databases market_kb,community_kb\n'
            '  python3 rag_query_multi.py "relocation tips" --all --k 5\n'
            '  python3 rag_query_multi.py --list\n'
        ),
    )
    parser.add_argument("query", nargs="?", help="Natural-language search query")
    parser.add_argument(
        "--databases",
        help="Comma-separated list of registered dataset names to query",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="query_all",
        help="Query all registered datasets",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of results per dataset (default: 3)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_results",
        help="Maximum total results to display",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered datasets and exit",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to manifest.json (default: ~/.real_estate_ai/manifest.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rag = MultiDatabaseRAG(manifest_path=args.manifest)

    # List mode
    if args.list:
        datasets = rag.manager.list_datasets()
        if not datasets:
            print("No datasets registered.")
        else:
            print(f"\nRegistered Datasets ({len(datasets)}):\n")
            for name, info in datasets.items():
                print(f"  {name}")
                print(f"    Description: {info['description']}")
                print(f"    Type: {info['data_type']}")
                tags = info.get("tags", [])
                if tags:
                    print(f"    Tags: {', '.join(tags)}")
                print()
        sys.exit(0)

    # Query mode requires a query string
    if not args.query:
        print("Error: a query string is required (or use --list).")
        sys.exit(1)

    # Determine which datasets to query
    if args.databases:
        names = [n.strip() for n in args.databases.split(",")]
        results = rag.query(names, args.query, args.k)
    else:
        # Default to --all
        results = rag.query_all(args.query, args.k)

    # Output
    if args.json_output:
        display = results[: args.max_results] if args.max_results else results
        print(json.dumps(display, indent=2, ensure_ascii=False))
    else:
        print(format_results_text(results, args.query, args.max_results))
