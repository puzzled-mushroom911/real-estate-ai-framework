#!/usr/bin/env python3
"""
Ingest YouTube Transcripts into ChromaDB Vector Database

Reads transcript .txt files and companion .json metadata files produced by
fetch_videos.py, chunks the text, embeds with sentence-transformers, and
stores in a ChromaDB collection. Skips videos already present (deduplication
by video_id).

Optionally registers the dataset in a RAG system manager manifest.

Dependencies:
    - chromadb
    - sentence-transformers
    - langchain-text-splitters

Usage:
    # Basic ingestion
    python3 ingest_to_rag.py ./transcripts/mychannel --db-name "my_channel"

    # Custom chunk size and database location
    python3 ingest_to_rag.py ./transcripts/mychannel \\
        --db-name "my_channel" \\
        --db-dir ./knowledge_bases/vectors \\
        --chunk-size 500 --overlap 50
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Lazy-loaded globals to avoid slow imports at startup
_embedding_model = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 50
DEFAULT_DB_DIR = Path("./knowledge_bases/vectors")


# ---------------------------------------------------------------------------
# Text Chunking
# ---------------------------------------------------------------------------


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks using LangChain's splitter.

    Uses RecursiveCharacterTextSplitter for intelligent splitting that
    respects sentence and paragraph boundaries where possible.

    Args:
        text: Raw transcript text.
        chunk_size: Target chunk size in characters.
        overlap: Character overlap between adjacent chunks.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text.strip())


# ---------------------------------------------------------------------------
# Embedding Model
# ---------------------------------------------------------------------------


def get_embedding_model():
    """Lazy-load the sentence-transformers embedding model.

    Returns:
        SentenceTransformer model instance.
    """
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        print(f"  Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


# ---------------------------------------------------------------------------
# ChromaDB Operations
# ---------------------------------------------------------------------------


def get_or_create_collection(db_path: Path, collection_name: str = "langchain"):
    """Open or create a ChromaDB collection at the given path.

    Args:
        db_path: Directory for the ChromaDB persistent storage.
        collection_name: Name of the collection within the database.

    Returns:
        ChromaDB Collection object, or None on failure.
    """
    import chromadb
    from chromadb.config import Settings

    db_path.mkdir(parents=True, exist_ok=True)

    try:
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return collection
    except Exception as e:
        print(f"  ERROR: Cannot open ChromaDB at {db_path}: {e}", file=sys.stderr)
        return None


def get_existing_video_ids(collection) -> set[str]:
    """Retrieve all video_id values already stored in a collection.

    Args:
        collection: ChromaDB Collection.

    Returns:
        Set of video_id strings already in the database.
    """
    if collection is None:
        return set()
    try:
        result = collection.get(include=["metadatas"])
        video_ids: set[str] = set()
        if result and result.get("metadatas"):
            for metadata in result["metadatas"]:
                vid = metadata.get("video_id")
                if vid:
                    video_ids.add(vid)
        return video_ids
    except Exception as e:
        print(f"  WARNING: Error reading existing IDs: {e}", file=sys.stderr)
        return set()


# ---------------------------------------------------------------------------
# Document Building & Ingestion
# ---------------------------------------------------------------------------


def build_documents(
    video_id: str,
    transcript: str,
    metadata: dict,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    """Build chunked documents with metadata for a single video.

    Creates two types of chunks:
      - transcript: Overlapping chunks of the full transcript text
      - description: A single chunk with the video title + description

    Args:
        video_id: YouTube video ID.
        transcript: Full plaintext transcript.
        metadata: Video metadata dict (from the .json file).
        chunk_size: Chunk size for text splitting.
        overlap: Overlap between chunks.

    Returns:
        List of document dicts with 'content' and 'metadata' keys.
    """
    base_meta = {
        "video_id": video_id,
        "title": metadata.get("title", "Untitled"),
        "url": metadata.get("url", f"https://www.youtube.com/watch?v={video_id}"),
        "upload_date": metadata.get("upload_date", ""),
        "channel_name": metadata.get("channel_name", ""),
        "channel_handle": metadata.get("channel_handle", ""),
        "duration_seconds": metadata.get("duration_seconds", 0),
        "view_count": metadata.get("view_count", 0),
        "source": f"youtube_{metadata.get('channel_handle', 'unknown').lstrip('@')}",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    documents: list[dict] = []

    # Transcript chunks
    if transcript:
        chunks = chunk_text(transcript, chunk_size=chunk_size, overlap=overlap)
        for i, chunk in enumerate(chunks):
            documents.append(
                {
                    "content": chunk,
                    "metadata": {
                        **base_meta,
                        "chunk_type": "transcript",
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                }
            )

    # Title + description as a separate searchable chunk
    title = metadata.get("title", "")
    description = metadata.get("description", "")
    title_desc = f"{title}\n\n{description}".strip()
    if title_desc:
        documents.append(
            {
                "content": title_desc,
                "metadata": {
                    **base_meta,
                    "chunk_type": "description",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            }
        )

    return documents


def ingest_documents(collection, documents: list[dict]) -> int:
    """Embed and store documents into a ChromaDB collection.

    Args:
        collection: ChromaDB Collection.
        documents: List of document dicts (each with 'content' and 'metadata').

    Returns:
        Number of documents successfully ingested.
    """
    if not documents or collection is None:
        return 0

    model = get_embedding_model()
    texts = [doc["content"] for doc in documents]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    ids: list[str] = []
    metadatas: list[dict] = []

    for doc in documents:
        video_id = doc["metadata"].get("video_id", "unknown")
        chunk_type = doc["metadata"].get("chunk_type", "unknown")
        chunk_index = doc["metadata"].get("chunk_index", 0)
        ids.append(f"{video_id}_{chunk_type}_{chunk_index}")

        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_meta: dict = {}
        for k, v in doc["metadata"].items():
            if v is None:
                clean_meta[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean_meta[k] = v
            else:
                clean_meta[k] = str(v)
        metadatas.append(clean_meta)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(documents)


# ---------------------------------------------------------------------------
# RAG System Manager Registration
# ---------------------------------------------------------------------------


def register_with_manager(
    db_dir: Path,
    db_name: str,
    transcript_dir: Path,
    video_count: int,
    chunk_count: int,
) -> None:
    """Register the database in the RAG system manager manifest.

    Looks for a manifest.json in the db_dir parent. Creates a minimal
    registration entry if the manager exists.

    Args:
        db_dir: Parent directory containing vector databases.
        db_name: Name of this database.
        transcript_dir: Source directory used for ingestion.
        video_count: Number of videos ingested.
        chunk_count: Total chunks stored.
    """
    manifest_path = db_dir / "manifest.json"

    # Load existing manifest or create new one
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "datasets": {},
            "version": "1.0",
            "created": datetime.now(timezone.utc).isoformat(),
        }

    manifest["datasets"][db_name] = {
        "description": f"YouTube channel transcripts from {transcript_dir.name}",
        "data_type": "youtube_channel",
        "source_info": {
            "transcript_dir": str(transcript_dir.resolve()),
            "video_count": video_count,
            "chunk_count": chunk_count,
        },
        "tags": ["youtube", "transcripts"],
        "path": str(db_dir / db_name),
        "created": datetime.now(timezone.utc).isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    manifest["updated"] = datetime.now(timezone.utc).isoformat()

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Registered in manifest: {manifest_path}")


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------


def ingest_transcripts(
    transcript_dir: Path,
    db_name: str,
    db_dir: Path,
    chunk_size: int,
    overlap: int,
) -> dict:
    """Run the full ingestion pipeline.

    1. Discover .txt transcript files with companion .json metadata
    2. Connect to (or create) the ChromaDB collection
    3. Skip videos already in the database
    4. Chunk, embed, and store new transcripts
    5. Register in RAG system manager

    Args:
        transcript_dir: Directory containing .txt and .json files.
        db_name: Name for the ChromaDB database subdirectory.
        db_dir: Parent directory for all vector databases.
        chunk_size: Target chunk size in characters.
        overlap: Character overlap between chunks.

    Returns:
        Summary dict with ingestion stats.
    """
    print(f"\n{'=' * 60}")
    print(f"RAG Ingestion: {db_name}")
    print(f"{'=' * 60}")
    print(f"  Source:     {transcript_dir}")
    print(f"  Database:   {db_dir / db_name}")
    print(f"  Chunk size: {chunk_size} chars, {overlap} overlap")

    result = {
        "db_name": db_name,
        "source_dir": str(transcript_dir),
        "videos_found": 0,
        "videos_skipped": 0,
        "videos_ingested": 0,
        "chunks_added": 0,
        "errors": [],
    }

    # Discover transcript files
    txt_files = sorted(transcript_dir.glob("**/*.txt"))
    if not txt_files:
        print("  No .txt transcript files found.")
        return result

    result["videos_found"] = len(txt_files)
    print(f"  Found {len(txt_files)} transcript files")

    # Open ChromaDB
    db_path = db_dir / db_name
    collection = get_or_create_collection(db_path)
    if collection is None:
        result["errors"].append("Failed to open ChromaDB")
        return result

    # Get existing video IDs for deduplication
    existing_ids = get_existing_video_ids(collection)
    print(f"  Existing videos in DB: {len(existing_ids)}")

    # Process each transcript
    for txt_path in txt_files:
        video_id = txt_path.stem
        json_path = txt_path.with_suffix(".json")

        # Deduplication check
        if video_id in existing_ids:
            result["videos_skipped"] += 1
            continue

        # Read transcript
        transcript = txt_path.read_text(encoding="utf-8").strip()
        if not transcript:
            result["errors"].append(f"{video_id}: Empty transcript file")
            continue

        # Read metadata (use minimal defaults if .json is missing)
        metadata: dict = {"video_id": video_id}
        if json_path.exists():
            try:
                metadata = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                result["errors"].append(f"{video_id}: Invalid JSON metadata")

        # Build and ingest documents
        documents = build_documents(
            video_id=video_id,
            transcript=transcript,
            metadata=metadata,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if documents:
            try:
                count = ingest_documents(collection, documents)
                result["videos_ingested"] += 1
                result["chunks_added"] += count
                title = metadata.get("title", video_id)[:50]
                print(f"    Ingested: {title}... ({count} chunks)")
            except Exception as e:
                result["errors"].append(f"{video_id}: Ingest error: {e}")
                print(f"    ERROR ingesting {video_id}: {e}", file=sys.stderr)

    # Register with RAG system manager
    if result["videos_ingested"] > 0:
        register_with_manager(
            db_dir=db_dir,
            db_name=db_name,
            transcript_dir=transcript_dir,
            video_count=result["videos_ingested"],
            chunk_count=result["chunks_added"],
        )

    # Print summary
    print(f"\n  --- Ingestion Summary ---")
    print(f"  Videos found:    {result['videos_found']}")
    print(f"  Already in DB:   {result['videos_skipped']}")
    print(f"  Newly ingested:  {result['videos_ingested']}")
    print(f"  Chunks added:    {result['chunks_added']}")
    if result["errors"]:
        print(f"  Errors:          {len(result['errors'])}")
        for err in result["errors"][:5]:
            print(f"    - {err}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest YouTube transcripts into a ChromaDB vector database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic ingestion
  python3 ingest_to_rag.py ./transcripts/mychannel --db-name "my_channel"

  # Custom settings
  python3 ingest_to_rag.py ./transcripts/mychannel \\
      --db-name "my_channel" \\
      --db-dir ~/knowledge_bases/vectors \\
      --chunk-size 800 --overlap 100
        """,
    )

    parser.add_argument(
        "transcript_dir",
        type=Path,
        help="Directory containing .txt transcript files and .json metadata files",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        required=True,
        help="Name for the ChromaDB database (creates a subdirectory)",
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=DEFAULT_DB_DIR,
        help=f"Parent directory for vector databases (default: {DEFAULT_DB_DIR})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Target chunk size in characters (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"Character overlap between chunks (default: {DEFAULT_OVERLAP})",
    )

    args = parser.parse_args()

    # Validate transcript directory
    if not args.transcript_dir.exists():
        print(
            f"ERROR: Transcript directory not found: {args.transcript_dir}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not args.transcript_dir.is_dir():
        print(
            f"ERROR: Not a directory: {args.transcript_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    result = ingest_transcripts(
        transcript_dir=args.transcript_dir,
        db_name=args.db_name,
        db_dir=args.db_dir,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    # Exit with error code if there were failures
    if result["errors"] and result["videos_ingested"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
