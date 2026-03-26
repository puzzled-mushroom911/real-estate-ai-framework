#!/usr/bin/env python3
"""
Create a ChromaDB vector knowledge base from document files.

Supports: .md, .pdf, .txt, .docx
Uses sentence-transformers/all-MiniLM-L6-v2 for embeddings.
Documents are split using LangChain's RecursiveCharacterTextSplitter.

Usage:
    python3 create_knowledge_base.py <source_dir> [options]

Examples:
    python3 create_knowledge_base.py ./documents
    python3 create_knowledge_base.py ./data --db-dir ./my_kb --chunk-size 500
    python3 create_knowledge_base.py ./docs --collection-name market_research
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    DirectoryLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

# Map of file extension -> (glob pattern, loader class, label)
FILE_TYPES: List[Tuple[str, str, type, str]] = [
    ("md", "**/*.md", TextLoader, "Markdown"),
    ("pdf", "**/*.pdf", PyPDFLoader, "PDF"),
    ("txt", "**/*.txt", TextLoader, "Text"),
    ("docx", "**/*.docx", Docx2txtLoader, "DOCX"),
]


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------
def create_knowledge_base(
    source_dir: str,
    db_dir: str = "./kb",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_OVERLAP,
    collection_name: str | None = None,
) -> Dict[str, int]:
    """
    Build a ChromaDB vector database from a directory of documents.

    Args:
        source_dir: Directory containing source documents.
        db_dir: Output directory for the ChromaDB database.
        chunk_size: Maximum characters per text chunk.
        chunk_overlap: Character overlap between consecutive chunks.
        collection_name: ChromaDB collection name. Auto-derived from
                         source directory name when not provided.

    Returns:
        Dict with stats: total_documents, total_chunks, and per-type counts.
    """
    source_path = Path(source_dir).resolve()
    db_path = Path(db_dir).resolve()

    # Derive collection name from directory if not specified
    if not collection_name:
        collection_name = source_path.name.lower().replace(" ", "_").replace("-", "_")

    print("=" * 80)
    print("RAG Knowledge Base Creator")
    print("=" * 80)
    print(f"  Source directory : {source_path}")
    print(f"  Database output  : {db_path}")
    print(f"  Collection name  : {collection_name}")
    print(f"  Chunk size       : {chunk_size}")
    print(f"  Chunk overlap    : {chunk_overlap}")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. Load documents by type
    # ------------------------------------------------------------------
    all_documents = []
    file_counts: Dict[str, int] = {}

    for ext, glob_pattern, loader_cls, label in FILE_TYPES:
        print(f"\nLoading {label} (.{ext}) files...")
        try:
            loader = DirectoryLoader(
                str(source_path),
                glob=glob_pattern,
                loader_cls=loader_cls,
                show_progress=True,
                use_multithreading=True,
            )
            docs = loader.load()
            all_documents.extend(docs)
            file_counts[ext] = len(docs)
            print(f"  Loaded {len(docs)} {label} file(s)")
        except Exception as exc:
            file_counts[ext] = 0
            print(f"  Warning: could not load {label} files: {exc}")

    if not all_documents:
        print("\nNo documents found! Ensure the source directory contains")
        print(".md, .pdf, .txt, or .docx files.")
        sys.exit(1)

    total_docs = len(all_documents)
    print(f"\nTotal documents loaded: {total_docs}")
    for ext, count in file_counts.items():
        if count:
            print(f"  .{ext}: {count}")

    # ------------------------------------------------------------------
    # 2. Split into chunks
    # ------------------------------------------------------------------
    print(f"\nSplitting documents (chunk_size={chunk_size}, overlap={chunk_overlap})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    splits = text_splitter.split_documents(all_documents)
    total_chunks = len(splits)
    print(f"  Created {total_chunks} text chunks")

    # ------------------------------------------------------------------
    # 3. Create embeddings & vector store
    # ------------------------------------------------------------------
    print(f"\nLoading embedding model ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("  Model loaded")

    # Clean rebuild — remove existing DB directory if present
    if db_path.exists():
        shutil.rmtree(db_path)
        print(f"  Removed existing database at {db_path}")
    db_path.mkdir(parents=True, exist_ok=True)

    print(f"\nBuilding vector database...")
    client = chromadb.PersistentClient(path=str(db_path))
    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        client=client,
        collection_name=collection_name,
    )

    # ------------------------------------------------------------------
    # 4. Report
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("KNOWLEDGE BASE CREATED SUCCESSFULLY")
    print("=" * 80)
    print(f"  Database location : {db_path}")
    print(f"  Collection        : {collection_name}")
    print(f"  Documents indexed : {total_docs}")
    print(f"  Chunks created    : {total_chunks}")
    print(f"\nQuery with:")
    print(f'  python3 rag_query.py "your question" --db-path {db_path}')
    print("=" * 80)

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        **{f"count_{ext}": c for ext, c in file_counts.items()},
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a ChromaDB vector knowledge base from document files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported file types: .md, .pdf, .txt, .docx\n\n"
            "Examples:\n"
            "  python3 create_knowledge_base.py ./documents\n"
            "  python3 create_knowledge_base.py ./data --db-dir ./my_kb\n"
            "  python3 create_knowledge_base.py ./docs --chunk-size 500 --overlap 100\n"
            "  python3 create_knowledge_base.py ./docs --collection-name my_collection\n"
        ),
    )
    parser.add_argument(
        "source_dir",
        help="Directory containing documents to index",
    )
    parser.add_argument(
        "--db-dir",
        default="./kb",
        help="Output directory for the vector database (default: ./kb)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Size of text chunks in characters (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"Overlap between chunks in characters (default: {DEFAULT_OVERLAP})",
    )
    parser.add_argument(
        "--collection-name",
        default=None,
        help="ChromaDB collection name (default: auto-derived from source directory)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    src = Path(args.source_dir)
    if not src.exists():
        print(f"Error: directory '{src}' does not exist.")
        sys.exit(1)
    if not src.is_dir():
        print(f"Error: '{src}' is not a directory.")
        sys.exit(1)

    create_knowledge_base(
        source_dir=str(src),
        db_dir=args.db_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        collection_name=args.collection_name,
    )
