#!/usr/bin/env python3
"""
RAG System Manager -- registry for all vector databases.

Maintains a manifest.json file that tracks every registered knowledge base
with its name, description, path, data type, source, and tags.

Usage:
    python3 rag_system_manager.py list
    python3 rag_system_manager.py register <name> <description> <path> <data_type> [options]
    python3 rag_system_manager.py path <name>
    python3 rag_system_manager.py summary

Examples:
    python3 rag_system_manager.py register market_data "Local MLS stats" ./market_kb documents
    python3 rag_system_manager.py register yt_content "YouTube transcripts" ./yt_kb youtube --source "channel" --tags youtube,content
    python3 rag_system_manager.py list
    python3 rag_system_manager.py path market_data
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MANIFEST_DIR = Path.home() / ".real_estate_ai"
DEFAULT_MANIFEST_FILE = DEFAULT_MANIFEST_DIR / "manifest.json"


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------
class RAGSystemManager:
    """
    Central registry for ChromaDB vector databases.

    Each dataset entry stores:
        name, description, path, data_type, source, tags, created, updated
    """

    def __init__(self, manifest_path: str | None = None):
        if manifest_path:
            self.manifest_file = Path(manifest_path).resolve()
        else:
            self.manifest_file = DEFAULT_MANIFEST_FILE

        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self.manifest: Dict[str, Any] = self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        """Load manifest from disk, or return a fresh structure."""
        if self.manifest_file.exists():
            with self.manifest_file.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return {
            "version": "1.0",
            "created": datetime.now(timezone.utc).isoformat(),
            "datasets": {},
        }

    def _save(self) -> None:
        """Persist the manifest to disk."""
        self.manifest["updated"] = datetime.now(timezone.utc).isoformat()
        with self.manifest_file.open("w", encoding="utf-8") as fh:
            json.dump(self.manifest, fh, indent=2, ensure_ascii=False)

    # -- public API ---------------------------------------------------------

    def register_dataset(
        self,
        name: str,
        description: str,
        path: str,
        data_type: str,
        source: str = "",
        tags: List[str] | None = None,
    ) -> str:
        """
        Register (or update) a dataset in the manifest.

        Args:
            name: Unique identifier (e.g. "market_data").
            description: Human-readable summary.
            path: Filesystem path to the ChromaDB directory.
            data_type: Category such as "documents", "youtube", "website".
            source: Freeform provenance string.
            tags: Optional list of tags for filtering.

        Returns:
            Resolved path to the dataset directory.
        """
        resolved = str(Path(path).resolve())
        now = datetime.now(timezone.utc).isoformat()

        self.manifest["datasets"][name] = {
            "description": description,
            "path": resolved,
            "data_type": data_type,
            "source": source,
            "tags": tags or [],
            "created": self.manifest["datasets"].get(name, {}).get("created", now),
            "updated": now,
        }
        self._save()
        print(f"Registered dataset: {name}")
        print(f"  Path: {resolved}")
        return resolved

    def list_datasets(self) -> Dict[str, Dict[str, Any]]:
        """Return all registered datasets."""
        return self.manifest.get("datasets", {})

    def get_dataset_path(self, name: str) -> Optional[str]:
        """Return the path for a dataset, or None if not found."""
        entry = self.manifest["datasets"].get(name)
        return entry["path"] if entry else None

    def get_datasets_by_tag(self, tag: str) -> List[str]:
        """Return names of datasets that carry a given tag."""
        return [
            n
            for n, info in self.manifest["datasets"].items()
            if tag in info.get("tags", [])
        ]

    def get_datasets_by_type(self, data_type: str) -> List[str]:
        """Return names of datasets of a given data_type."""
        return [
            n
            for n, info in self.manifest["datasets"].items()
            if info.get("data_type") == data_type
        ]

    def print_summary(self) -> None:
        """Print a human-readable summary of the registry."""
        datasets = self.manifest.get("datasets", {})
        print("=" * 80)
        print("RAG SYSTEM -- DATASET REGISTRY")
        print("=" * 80)
        print(f"  Manifest : {self.manifest_file}")
        print(f"  Datasets : {len(datasets)}")
        print("=" * 80)

        if not datasets:
            print("\n  (no datasets registered)")
            return

        # Collect tag and type stats
        all_tags: Dict[str, int] = {}
        all_types: Dict[str, int] = {}
        for info in datasets.values():
            dt = info.get("data_type", "unknown")
            all_types[dt] = all_types.get(dt, 0) + 1
            for t in info.get("tags", []):
                all_tags[t] = all_tags.get(t, 0) + 1

        print("\nBy type:")
        for dt, count in sorted(all_types.items()):
            print(f"  {dt}: {count}")

        if all_tags:
            print("\nBy tag:")
            for tag, count in sorted(all_tags.items(), key=lambda x: -x[1]):
                print(f"  {tag}: {count}")

        print("\nDatasets:")
        print("-" * 80)
        for name, info in datasets.items():
            print(f"\n  {name}")
            print(f"    Description : {info['description']}")
            print(f"    Type        : {info['data_type']}")
            print(f"    Path        : {info['path']}")
            if info.get("source"):
                print(f"    Source      : {info['source']}")
            if info.get("tags"):
                print(f"    Tags        : {', '.join(info['tags'])}")
            print(f"    Updated     : {info.get('updated', 'N/A')}")
        print("\n" + "=" * 80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the registry of RAG vector databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python3 rag_system_manager.py register market_data "MLS stats" ./market_kb documents\n'
            "  python3 rag_system_manager.py list\n"
            "  python3 rag_system_manager.py path market_data\n"
            "  python3 rag_system_manager.py summary\n"
        ),
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help=f"Path to manifest.json (default: {DEFAULT_MANIFEST_FILE})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # -- list ---------------------------------------------------------------
    subparsers.add_parser("list", help="List all registered datasets")

    # -- summary ------------------------------------------------------------
    subparsers.add_parser("summary", help="Show detailed registry summary")

    # -- register -----------------------------------------------------------
    reg = subparsers.add_parser("register", help="Register a new dataset")
    reg.add_argument("name", help="Unique dataset name")
    reg.add_argument("description", help="Human-readable description")
    reg.add_argument("path", help="Path to the ChromaDB database directory")
    reg.add_argument(
        "data_type",
        help="Data type (e.g. documents, youtube, website)",
    )
    reg.add_argument("--source", default="", help="Source provenance string")
    reg.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (e.g. youtube,content,strategy)",
    )

    # -- path ---------------------------------------------------------------
    p = subparsers.add_parser("path", help="Print path for a dataset name")
    p.add_argument("name", help="Dataset name")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.command:
        print("Error: a command is required (list, register, path, summary).")
        print("Run with --help for usage.")
        sys.exit(1)

    manager = RAGSystemManager(manifest_path=args.manifest)

    if args.command == "list":
        datasets = manager.list_datasets()
        if not datasets:
            print("No datasets registered.")
        else:
            print(f"\nRegistered Datasets ({len(datasets)}):")
            for name in datasets:
                print(f"  - {name}")

    elif args.command == "summary":
        manager.print_summary()

    elif args.command == "register":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        manager.register_dataset(
            name=args.name,
            description=args.description,
            path=args.path,
            data_type=args.data_type,
            source=args.source,
            tags=tags,
        )

    elif args.command == "path":
        result = manager.get_dataset_path(args.name)
        if result:
            print(result)
        else:
            print(f"Dataset '{args.name}' not found.")
            sys.exit(1)
