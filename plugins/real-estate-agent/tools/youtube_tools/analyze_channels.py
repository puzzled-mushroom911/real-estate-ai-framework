#!/usr/bin/env python3
"""
Analyze YouTube Channel Content from RAG Databases

Query ChromaDB vector databases for strategic content insights: topic
distribution, top performers, channel comparisons, content gaps, and
AI-powered recommendations.

Dependencies:
    - chromadb
    - sentence-transformers

Usage:
    python3 analyze_channels.py topics --database my_channel
    python3 analyze_channels.py top --database my_channel --limit 10
    python3 analyze_channels.py compare --database my_channel --compare-db competitor
    python3 analyze_channels.py gaps --database my_channel --compare-db competitor
    python3 analyze_channels.py recommend --database my_channel
    python3 analyze_channels.py search "best neighborhoods" --database my_channel
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DB_DIR = Path("./knowledge_bases/vectors")

# Lazy-loaded globals
_embedding_model = None


# ---------------------------------------------------------------------------
# ChromaDB Helpers
# ---------------------------------------------------------------------------


def get_embedding_model():
    """Lazy-load the sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def load_collection(db_path: Path, collection_name: str = "langchain"):
    """Load a ChromaDB collection from disk.

    Args:
        db_path: Path to the ChromaDB persistent storage directory.
        collection_name: Name of the collection to open.

    Returns:
        Tuple of (chromadb_client, collection) or (None, None) on failure.
    """
    import chromadb
    from chromadb.config import Settings

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        return None, None

    try:
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name=collection_name)
        return client, collection
    except Exception as e:
        # Try common alternative collection names
        try:
            client = chromadb.PersistentClient(
                path=str(db_path),
                settings=Settings(anonymized_telemetry=False),
            )
            collections = client.list_collections()
            if collections:
                collection = collections[0]
                return client, collection
        except Exception:
            pass
        print(f"ERROR: Cannot open database at {db_path}: {e}", file=sys.stderr)
        return None, None


def get_all_videos(collection) -> list[dict]:
    """Extract unique video metadata from a ChromaDB collection.

    Deduplicates by video_id since each video has multiple chunks.

    Args:
        collection: ChromaDB Collection object.

    Returns:
        List of unique video metadata dicts.
    """
    result = collection.get(include=["metadatas"])
    seen: set[str] = set()
    videos: list[dict] = []

    for meta in result.get("metadatas", []):
        vid = meta.get("video_id", "")
        if vid and vid not in seen:
            seen.add(vid)
            videos.append(meta)

    return videos


def get_all_documents(collection) -> list[dict]:
    """Retrieve all documents with their content and metadata.

    Args:
        collection: ChromaDB Collection object.

    Returns:
        List of dicts with 'content' and 'metadata' keys.
    """
    result = collection.get(include=["documents", "metadatas"])
    documents: list[dict] = []
    for doc, meta in zip(
        result.get("documents", []), result.get("metadatas", [])
    ):
        documents.append({"content": doc, "metadata": meta})
    return documents


# ---------------------------------------------------------------------------
# Analysis Commands
# ---------------------------------------------------------------------------


def cmd_topics(collection, limit: int = 20) -> None:
    """Analyze topic distribution across videos by extracting title keywords.

    Groups videos by common title keywords and reports view count totals
    for each topic cluster.

    Args:
        collection: ChromaDB Collection.
        limit: Maximum topics to display.
    """
    videos = get_all_videos(collection)

    if not videos:
        print("No videos found in database.")
        return

    print(f"\n{'=' * 60}")
    print(f"TOPIC DISTRIBUTION ({len(videos)} videos)")
    print(f"{'=' * 60}\n")

    # Extract topic signals from titles
    # Common real estate / YouTube keywords to look for
    topic_keywords = {
        "neighborhood": ["neighborhood", "area", "community", "suburb"],
        "cost_of_living": ["cost", "expensive", "affordable", "price", "budget"],
        "pros_and_cons": ["pros", "cons", "good", "bad", "worst", "best"],
        "housing_market": ["market", "housing", "home", "house", "buy", "buying"],
        "relocation": ["moving", "relocate", "relocation", "move"],
        "lifestyle": ["lifestyle", "living", "life", "things to do"],
        "schools": ["school", "education"],
        "safety": ["safe", "safety", "crime", "dangerous"],
        "jobs": ["job", "work", "career", "employment", "salary"],
        "food_dining": ["food", "restaurant", "eat", "dining"],
        "outdoor": ["beach", "park", "outdoor", "nature", "water"],
        "tour": ["tour", "walkthrough", "drive", "visit"],
        "update": ["update", "2024", "2025", "2026", "new"],
        "tips": ["tip", "advice", "guide", "how to", "mistake", "avoid"],
    }

    topic_counts: dict[str, int] = Counter()
    topic_views: dict[str, int] = defaultdict(int)
    topic_videos: dict[str, list[str]] = defaultdict(list)

    for v in videos:
        title = v.get("title", "").lower()
        views = v.get("view_count", 0)
        if isinstance(views, str):
            try:
                views = int(views)
            except ValueError:
                views = 0

        matched_topics: set[str] = set()
        for topic, keywords in topic_keywords.items():
            if any(kw in title for kw in keywords):
                matched_topics.add(topic)

        if not matched_topics:
            matched_topics.add("other")

        for topic in matched_topics:
            topic_counts[topic] += 1
            topic_views[topic] += views
            topic_videos[topic].append(v.get("title", "Untitled")[:50])

    # Display results
    print(
        f"{'Topic':<20} {'Videos':<10} {'Total Views':<15} {'Avg Views':<12}"
    )
    print("-" * 57)

    for topic, count in topic_counts.most_common(limit):
        avg_views = topic_views[topic] // count if count else 0
        print(
            f"{topic:<20} {count:<10} {topic_views[topic]:>12,}   {avg_views:>9,}"
        )

    # Show top examples per topic
    print(f"\n{'=' * 60}")
    print("TOP EXAMPLES PER TOPIC")
    print(f"{'=' * 60}")
    for topic, count in topic_counts.most_common(5):
        print(f"\n  {topic.upper().replace('_', ' ')} ({count} videos):")
        for title in topic_videos[topic][:3]:
            print(f"    - {title}")


def cmd_top(collection, limit: int = 10) -> None:
    """Show top-performing videos by view count.

    Args:
        collection: ChromaDB Collection.
        limit: Number of videos to show.
    """
    videos = get_all_videos(collection)

    if not videos:
        print("No videos found in database.")
        return

    # Parse view counts and sort
    for v in videos:
        views = v.get("view_count", 0)
        if isinstance(views, str):
            try:
                v["_views"] = int(views)
            except ValueError:
                v["_views"] = 0
        else:
            v["_views"] = views or 0

    videos.sort(key=lambda x: x["_views"], reverse=True)

    print(f"\n{'=' * 60}")
    print(f"TOP {limit} VIDEOS BY VIEWS")
    print(f"{'=' * 60}\n")

    for i, v in enumerate(videos[:limit], 1):
        title = v.get("title", "Untitled")
        views = v["_views"]
        duration = v.get("duration_seconds", 0)
        date = v.get("upload_date", v.get("publish_date", ""))
        url = v.get("url", v.get("video_url", ""))
        channel = v.get("channel_name", "")

        print(f"{i:>3}. {title[:55]}")
        print(f"     Views: {views:,}  |  Date: {date}  |  Duration: {duration}s")
        if channel:
            print(f"     Channel: {channel}")
        if url:
            print(f"     {url}")
        print()


def cmd_compare(collection_a, collection_b, name_a: str, name_b: str) -> None:
    """Compare two channels side by side.

    Shows total videos, views, average views, and topic focus for each.

    Args:
        collection_a: First channel's ChromaDB Collection.
        collection_b: Second channel's ChromaDB Collection.
        name_a: Display name for first channel.
        name_b: Display name for second channel.
    """
    print(f"\n{'=' * 60}")
    print(f"CHANNEL COMPARISON")
    print(f"{'=' * 60}")

    for name, collection in [(name_a, collection_a), (name_b, collection_b)]:
        videos = get_all_videos(collection)

        total_views = 0
        for v in videos:
            views = v.get("view_count", 0)
            if isinstance(views, str):
                try:
                    views = int(views)
                except ValueError:
                    views = 0
            total_views += views

        avg_views = total_views // len(videos) if videos else 0

        # Extract title words for topic focus
        word_counts: Counter = Counter()
        stop_words = {
            "the", "a", "an", "in", "to", "of", "and", "is", "for", "on",
            "it", "my", "i", "you", "your", "we", "our", "this", "that",
            "with", "from", "at", "by", "or", "not", "are", "was", "be",
            "but", "if", "so", "do", "has", "how", "what", "why", "when",
            "will", "can", "|", "-", "about", "its", "just", "all", "new",
        }
        for v in videos:
            title_words = v.get("title", "").lower().split()
            for word in title_words:
                word = word.strip(",.!?()[]{}\"'#")
                if len(word) > 2 and word not in stop_words:
                    word_counts[word] += 1

        top_words = [w for w, _ in word_counts.most_common(8)]

        print(f"\n  {name}")
        print(f"  {'-' * 40}")
        print(f"  Total Videos:      {len(videos)}")
        print(f"  Total Views:       {total_views:,}")
        print(f"  Avg Views/Video:   {avg_views:,}")
        print(f"  Top Keywords:      {', '.join(top_words)}")


def cmd_gaps(
    own_collection, competitor_collection, own_name: str, competitor_name: str
) -> None:
    """Find content gaps: topics the competitor covers that you do not.

    Performs keyword extraction on both channels' video titles and identifies
    significant terms present in the competitor's content but absent or
    underrepresented in yours.

    Args:
        own_collection: Your channel's ChromaDB Collection.
        competitor_collection: Competitor's ChromaDB Collection.
        own_name: Your channel display name.
        competitor_name: Competitor channel display name.
    """
    print(f"\n{'=' * 60}")
    print(f"CONTENT GAPS: What {competitor_name} covers that {own_name} doesn't")
    print(f"{'=' * 60}\n")

    stop_words = {
        "the", "a", "an", "in", "to", "of", "and", "is", "for", "on",
        "it", "my", "i", "you", "your", "we", "our", "this", "that",
        "with", "from", "at", "by", "or", "not", "are", "was", "be",
        "but", "if", "so", "do", "has", "how", "what", "why", "when",
        "will", "can", "|", "-", "about", "its", "just", "all", "new",
    }

    def extract_keywords(collection) -> Counter:
        videos = get_all_videos(collection)
        word_freq: Counter = Counter()
        for v in videos:
            words = v.get("title", "").lower().split()
            for word in words:
                word = word.strip(",.!?()[]{}\"'#")
                if len(word) > 2 and word not in stop_words:
                    word_freq[word] += 1
        return word_freq

    own_keywords = extract_keywords(own_collection)
    competitor_keywords = extract_keywords(competitor_collection)

    # Find keywords that appear in competitor but not (or rarely) in own content
    gaps: list[tuple[str, int, int]] = []
    for word, comp_count in competitor_keywords.most_common(100):
        own_count = own_keywords.get(word, 0)
        if comp_count >= 2 and own_count <= comp_count // 3:
            gaps.append((word, comp_count, own_count))

    if not gaps:
        print("No significant content gaps found. Good coverage!")
        return

    print(
        f"{'Keyword':<25} {competitor_name + ' count':<20} {own_name + ' count':<20}"
    )
    print("-" * 65)

    for keyword, comp_count, own_count in gaps[:20]:
        print(f"{keyword:<25} {comp_count:<20} {own_count:<20}")

    # Show competitor video titles for top gap keywords
    comp_videos = get_all_videos(competitor_collection)
    print(f"\nSample competitor videos covering gap topics:")
    shown = 0
    for keyword, _, _ in gaps[:5]:
        for v in comp_videos:
            if keyword in v.get("title", "").lower() and shown < 10:
                views = v.get("view_count", 0)
                if isinstance(views, str):
                    try:
                        views = int(views)
                    except ValueError:
                        views = 0
                print(f"  [{keyword}] {v.get('title', '')[:55]} ({views:,} views)")
                shown += 1
                break


def cmd_recommend(collection, limit: int = 10) -> None:
    """Suggest next video topics based on performance patterns.

    Analyzes which title keywords correlate with higher view counts
    and recommends topic combinations for future content.

    Args:
        collection: ChromaDB Collection.
        limit: Number of recommendations.
    """
    videos = get_all_videos(collection)

    if not videos:
        print("No videos found in database.")
        return

    print(f"\n{'=' * 60}")
    print("CONTENT RECOMMENDATIONS")
    print(f"{'=' * 60}\n")

    stop_words = {
        "the", "a", "an", "in", "to", "of", "and", "is", "for", "on",
        "it", "my", "i", "you", "your", "we", "our", "this", "that",
        "with", "from", "at", "by", "or", "not", "are", "was", "be",
        "but", "if", "so", "do", "has", "how", "what", "why", "when",
        "will", "can", "|", "-", "about", "its", "just", "all", "new",
    }

    # Keyword → views mapping
    keyword_views: dict[str, list[int]] = defaultdict(list)
    keyword_titles: dict[str, list[str]] = defaultdict(list)

    for v in videos:
        views = v.get("view_count", 0)
        if isinstance(views, str):
            try:
                views = int(views)
            except ValueError:
                views = 0

        title = v.get("title", "")
        words = title.lower().split()
        for word in words:
            word = word.strip(",.!?()[]{}\"'#")
            if len(word) > 2 and word not in stop_words:
                keyword_views[word].append(views)
                keyword_titles[word].append(title[:50])

    # Score keywords: average views * log(frequency) for balanced ranking
    import math

    scored: list[tuple[str, float, int, int]] = []
    for keyword, views_list in keyword_views.items():
        if len(views_list) < 2:
            continue  # Need at least 2 videos to establish a pattern
        avg_views = sum(views_list) // len(views_list)
        frequency = len(views_list)
        score = avg_views * math.log2(frequency + 1)
        scored.append((keyword, score, avg_views, frequency))

    scored.sort(key=lambda x: x[1], reverse=True)

    print("High-performing topic keywords (by views x frequency):\n")
    print(f"{'Keyword':<20} {'Score':<12} {'Avg Views':<12} {'Frequency':<10}")
    print("-" * 54)

    for keyword, score, avg_views, freq in scored[:limit]:
        print(f"{keyword:<20} {score:>10,.0f}  {avg_views:>10,}  {freq:>8}")

    # Suggest topic combinations
    print(f"\nSuggested topic combinations (pair high-performing keywords):\n")
    top_keywords = [k for k, _, _, _ in scored[:8]]
    suggestions_shown = 0
    for i, kw1 in enumerate(top_keywords):
        for kw2 in top_keywords[i + 1 :]:
            # Check if this combination already exists
            combo_exists = False
            for v in videos:
                title_lower = v.get("title", "").lower()
                if kw1 in title_lower and kw2 in title_lower:
                    combo_exists = True
                    break
            if not combo_exists and suggestions_shown < limit:
                print(f"  - {kw1} + {kw2}")
                suggestions_shown += 1


def cmd_search(
    collection, query: str, limit: int = 5
) -> None:
    """Semantic search across channel content.

    Uses the embedding model to find the most relevant content chunks
    for a given query.

    Args:
        collection: ChromaDB Collection.
        query: Natural language search query.
        limit: Number of results to return.
    """
    print(f"\n{'=' * 60}")
    print(f"SEARCH: \"{query}\"")
    print(f"{'=' * 60}\n")

    model = get_embedding_model()
    query_embedding = model.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        print("No results found.")
        return

    seen_videos: set[str] = set()
    rank = 0

    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        video_id = meta.get("video_id", "")
        # Show each video at most once
        if video_id in seen_videos:
            continue
        seen_videos.add(video_id)
        rank += 1

        title = meta.get("title", "Untitled")
        url = meta.get("url", meta.get("video_url", ""))
        views = meta.get("view_count", 0)
        channel = meta.get("channel_name", "")
        relevance = 1.0 - distance  # Convert distance to similarity

        print(f"{rank}. {title[:60]}")
        print(f"   Relevance: {relevance:.3f}  |  Views: {views:,}")
        if channel:
            print(f"   Channel: {channel}")
        if url:
            print(f"   URL: {url}")
        # Show content preview
        preview = doc[:200].replace("\n", " ").strip()
        print(f"   Preview: {preview}...")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def resolve_db_path(db_name: str, db_dir: Path) -> Path:
    """Resolve a database name to a full path.

    If db_name is already an absolute path or relative path that exists,
    use it directly. Otherwise, treat it as a subdirectory of db_dir.

    Args:
        db_name: Database name or path.
        db_dir: Default parent directory for databases.

    Returns:
        Resolved Path to the database.
    """
    candidate = Path(db_name)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    return db_dir / db_name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze YouTube channel content from ChromaDB RAG databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  topics    - Topic distribution with view counts
  top       - Top performing videos by engagement
  compare   - Compare two channels side by side
  gaps      - Content gaps (competitor topics you haven't covered)
  recommend - Suggest next video topics
  search    - Semantic search across channel content

Examples:
  python3 analyze_channels.py topics --database my_channel
  python3 analyze_channels.py top --database my_channel --limit 20
  python3 analyze_channels.py compare --database my_channel --compare-db competitor
  python3 analyze_channels.py gaps --database my_channel --compare-db competitor
  python3 analyze_channels.py recommend --database my_channel
  python3 analyze_channels.py search "waterfront homes" --database my_channel
        """,
    )

    parser.add_argument(
        "command",
        choices=["topics", "top", "compare", "gaps", "recommend", "search"],
        help="Analysis command to run",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Search query (required for 'search' command)",
    )
    parser.add_argument(
        "--database",
        type=str,
        required=True,
        help="ChromaDB database name or path",
    )
    parser.add_argument(
        "--compare-db",
        type=str,
        default=None,
        help="Second database for comparison (required for 'compare' and 'gaps')",
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=DEFAULT_DB_DIR,
        help=f"Parent directory for databases (default: {DEFAULT_DB_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results to display (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (where supported)",
    )

    args = parser.parse_args()

    # Validate command-specific requirements
    if args.command == "search" and not args.query:
        parser.error("The 'search' command requires a query argument.")

    if args.command in ("compare", "gaps") and not args.compare_db:
        parser.error(
            f"The '{args.command}' command requires --compare-db."
        )

    # Load primary database
    db_path = resolve_db_path(args.database, args.db_dir)
    _, collection = load_collection(db_path)
    if collection is None:
        print(f"ERROR: Could not load database: {db_path}", file=sys.stderr)
        sys.exit(1)

    # Load comparison database if needed
    comp_collection = None
    if args.compare_db:
        comp_path = resolve_db_path(args.compare_db, args.db_dir)
        _, comp_collection = load_collection(comp_path)
        if comp_collection is None:
            print(
                f"ERROR: Could not load comparison database: {comp_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Dispatch to command handler
    if args.command == "topics":
        cmd_topics(collection, limit=args.limit)
    elif args.command == "top":
        cmd_top(collection, limit=args.limit)
    elif args.command == "compare":
        cmd_compare(
            collection,
            comp_collection,
            name_a=args.database,
            name_b=args.compare_db,
        )
    elif args.command == "gaps":
        cmd_gaps(
            collection,
            comp_collection,
            own_name=args.database,
            competitor_name=args.compare_db,
        )
    elif args.command == "recommend":
        cmd_recommend(collection, limit=args.limit)
    elif args.command == "search":
        cmd_search(collection, query=args.query, limit=args.limit)


if __name__ == "__main__":
    main()
