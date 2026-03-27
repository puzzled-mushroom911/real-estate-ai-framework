#!/usr/bin/env python3
"""
Pre-configured consulting scenarios for real estate YouTube creators.

Ships with preset queries for common needs (channel setup, content ideas,
lead generation, SEO, etc.) that target a strategy knowledge base and an
examples knowledge base.  Database paths and names are read from an
optional agent_profile.yaml; sensible defaults are used when the file is
missing.

Usage:
    python3 rag_youtube_helper.py <scenario> [--max 5]
    python3 rag_youtube_helper.py --custom "question" [--mode both] [--k 5]

Examples:
    python3 rag_youtube_helper.py content-ideas
    python3 rag_youtube_helper.py lead-generation --max 8
    python3 rag_youtube_helper.py --custom "video editing workflow" --mode strategy
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Default database paths -- override via agent_profile.yaml or CLI
DEFAULT_STRATEGY_DB = "./kb_youtube_strategy"
DEFAULT_EXAMPLES_DB = "./kb_youtube_examples"

# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------
SCENARIOS: Dict[str, Dict[str, Any]] = {
    "channel-setup": {
        "query": "How to set up and launch a real estate YouTube channel",
        "description": "Complete channel setup guide",
        "databases": "both",
        "k": 5,
    },
    "content-ideas": {
        "query": "Best video content ideas for real estate agents on YouTube",
        "description": "Video content strategy and ideas",
        "databases": "both",
        "k": 6,
    },
    "lead-generation": {
        "query": "How to generate real estate leads from YouTube videos",
        "description": "Lead generation strategies from YouTube",
        "databases": "both",
        "k": 5,
    },
    "thumbnails-titles": {
        "query": "YouTube thumbnail and title best practices for real estate",
        "description": "Thumbnail and title optimization",
        "databases": "strategy",
        "k": 4,
    },
    "seo-strategy": {
        "query": "YouTube SEO and discoverability for real estate agents",
        "description": "SEO and video ranking strategies",
        "databases": "both",
        "k": 5,
    },
    "engagement": {
        "query": "How to increase engagement and subscribers on a real estate YouTube channel",
        "description": "Subscriber and engagement growth",
        "databases": "both",
        "k": 5,
    },
    "neighborhood-tours": {
        "query": "Best practices for neighborhood and area tour videos",
        "description": "Neighborhood and area tour content",
        "databases": "examples",
        "k": 5,
    },
    "relocation-content": {
        "query": "Creating relocation and moving guide content for YouTube",
        "description": "Relocation buyer content strategy",
        "databases": "both",
        "k": 5,
    },
}


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------
def load_profile_config() -> Dict[str, str]:
    """
    Attempt to read database paths from agent_profile.yaml.

    Expected YAML structure (only the youtube_rag section is used):

        youtube_rag:
          strategy_db: /path/to/strategy_kb
          examples_db: /path/to/examples_kb

    Returns a dict with keys 'strategy_db' and 'examples_db'.
    Falls back to defaults when the file is missing or incomplete.
    """
    defaults = {
        "strategy_db": DEFAULT_STRATEGY_DB,
        "examples_db": DEFAULT_EXAMPLES_DB,
    }

    profile_path = Path("agent_profile.yaml")
    if not profile_path.exists():
        return defaults

    try:
        import yaml  # optional dependency

        with profile_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        yt = data.get("youtube_rag", {})
        return {
            "strategy_db": yt.get("strategy_db", defaults["strategy_db"]),
            "examples_db": yt.get("examples_db", defaults["examples_db"]),
        }
    except ImportError:
        # PyYAML not installed -- fall back to defaults silently
        return defaults
    except Exception:
        return defaults


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------
def _query_db(
    db_path: str, question: str, k: int, embeddings: HuggingFaceEmbeddings
) -> List[Dict[str, Any]]:
    """Run a semantic search against a single ChromaDB database."""
    resolved = Path(db_path).resolve()
    if not resolved.exists():
        print(f"Warning: database not found at {resolved} -- skipping.")
        return []

    try:
        client = chromadb.PersistentClient(path=str(resolved))
        collections = client.list_collections()
        if not collections:
            return []
        collection_name = collections[0].name

        vectorstore = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        raw = vectorstore.similarity_search_with_score(question, k=k)
        return [
            {
                "score": round(float(score), 4),
                "source": doc.metadata.get("source", "unknown"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "db": db_path,
            }
            for doc, score in raw
        ]
    except Exception as exc:
        print(f"Warning: error querying {db_path}: {exc}")
        return []


def run_query(
    question: str,
    mode: str = "both",
    k: int = 5,
    max_results: int | None = None,
    config: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Execute a YouTube consulting query.

    Args:
        question: Natural-language query.
        mode: Which databases to search -- "both", "strategy", or "examples".
        k: Results per database.
        max_results: Cap on total results returned.
        config: Dict with 'strategy_db' and 'examples_db' paths.

    Returns:
        Relevance-sorted list of result dicts.
    """
    cfg = config or load_profile_config()
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    results: List[Dict[str, Any]] = []

    if mode in ("both", "strategy"):
        results.extend(_query_db(cfg["strategy_db"], question, k, embeddings))
    if mode in ("both", "examples"):
        results.extend(_query_db(cfg["examples_db"], question, k, embeddings))

    # Sort by relevance (lower distance = better)
    results.sort(key=lambda r: r["score"])

    if max_results:
        results = results[:max_results]

    return results


def format_results(
    results: List[Dict[str, Any]], title: str
) -> str:
    """Render results as human-readable text."""
    if not results:
        return "No results found."

    lines = [
        "=" * 80,
        f"  {title.upper()}",
        "=" * 80,
        f"\n  {len(results)} result(s)\n",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(f"--- Result {i} (score: {r['score']}) ---")
        lines.append(f"Source: {r['source']}")
        meta = r.get("metadata", {})
        if meta.get("video_title"):
            lines.append(f"Video : {meta['video_title']}")
        lines.append(f"\n{r['content']}\n")
        lines.append("-" * 80)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-configured YouTube consulting queries for real estate agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Preset scenarios:\n"
            + "\n".join(
                f"  {key:22s} {info['description']}"
                for key, info in SCENARIOS.items()
            )
            + "\n\nExamples:\n"
            "  python3 rag_youtube_helper.py content-ideas\n"
            "  python3 rag_youtube_helper.py lead-generation --max 8\n"
            '  python3 rag_youtube_helper.py --custom "editing tips" --mode strategy\n'
        ),
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=list(SCENARIOS.keys()),
        help="Name of a preset consulting scenario",
    )
    parser.add_argument(
        "--custom",
        default=None,
        help="Run a custom query instead of a preset scenario",
    )
    parser.add_argument(
        "--mode",
        choices=["both", "strategy", "examples"],
        default="both",
        help="Which databases to search (default: both)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Results per database (default: 5)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_results",
        help="Maximum total results to display",
    )
    parser.add_argument(
        "--strategy-db",
        default=None,
        help=f"Path to strategy knowledge base (default: {DEFAULT_STRATEGY_DB})",
    )
    parser.add_argument(
        "--examples-db",
        default=None,
        help=f"Path to examples knowledge base (default: {DEFAULT_EXAMPLES_DB})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Build config from profile + CLI overrides
    config = load_profile_config()
    if args.strategy_db:
        config["strategy_db"] = args.strategy_db
    if args.examples_db:
        config["examples_db"] = args.examples_db

    if args.custom:
        # Custom query mode
        title = f"Custom Query -- mode: {args.mode}"
        results = run_query(
            question=args.custom,
            mode=args.mode,
            k=args.k,
            max_results=args.max_results,
            config=config,
        )
        print(format_results(results, title))

    elif args.scenario:
        # Preset scenario mode
        scenario = SCENARIOS[args.scenario]
        title = scenario["description"]
        results = run_query(
            question=scenario["query"],
            mode=scenario["databases"],
            k=scenario["k"],
            max_results=args.max_results,
            config=config,
        )
        print(format_results(results, title))

    else:
        print("Error: provide a scenario name or use --custom \"your question\".")
        print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
        print("Run with --help for full usage.")
        sys.exit(1)
