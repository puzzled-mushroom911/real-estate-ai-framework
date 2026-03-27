#!/usr/bin/env python3
"""
Convert YouTube Transcript to Structured Blog Post

Reads a raw transcript .txt file, cleans and normalizes the text, extracts
structural elements (sections, key points, callouts), and outputs both a
structured JSON template and a markdown blog post. The JSON structure is
designed to be fed into a CMS or further processed by an AI agent.

This script handles the CLEANING and STRUCTURING of transcript text.
The actual AI-powered rewriting (voice matching, SEO optimization) is
intended to be done by a downstream agent (e.g., Claude).

Dependencies:
    - None (stdlib only)

Usage:
    python3 transcript_to_blog.py transcript.txt --title "Video Title"
    python3 transcript_to_blog.py transcript.txt --title "My Video" --agent-name "Agent Name"
    python3 transcript_to_blog.py transcript.txt --output blog.md --style conversational
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Transcript Cleaning
# ---------------------------------------------------------------------------

# Common filler words and verbal tics from speech-to-text
FILLER_PATTERNS = [
    r"\b(um|uh|umm|uhh|hmm|hm)\b",
    r"\b(you know)\b",
    r"\b(like)\b(?=\s+(like|you|i|we|the|a|so|um))",  # Only "like" as filler, not verb
    r"\b(i mean)\b",
    r"\b(kind of|kinda)\b",
    r"\b(sort of|sorta)\b",
    r"\b(basically)\b",
    r"\b(actually)\b(?=\s*,)",  # "actually," as filler start
    r"\b(right)\b(?=\s*[,.]?\s*(so|and|but|now))",  # "right, so..."
]

# Common transcription errors in real estate content
TRANSCRIPTION_FIXES = {
    r"\bst pete\b": "St. Pete",
    r"\bst\. pete\b": "St. Pete",
    r"\btampa bay\b": "Tampa Bay",
    r"\bhoa\b": "HOA",
    r"\bmls\b": "MLS",
    r"\bsqft\b": "sq ft",
    r"\bsquare foot\b": "square feet",
    r"\bbedroom\b": "bedroom",
    r"\bbathroom\b": "bathroom",
    r"\bcondo\b": "condo",
    r"\btownhome\b": "townhome",
    r"\b(\d+)k\b": r"\g<1>,000",  # "300k" → "300,000"
}


def clean_transcript(text: str) -> str:
    """Clean raw transcript text by removing filler words and fixing errors.

    Args:
        text: Raw transcript text.

    Returns:
        Cleaned text with fillers removed and common errors fixed.
    """
    cleaned = text.strip()

    # Remove filler words
    for pattern in FILLER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Fix common transcription errors
    for pattern, replacement in TRANSCRIPTION_FIXES.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Normalize whitespace (collapse multiple spaces, clean up around punctuation)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"([.!?])\s*([A-Z])", r"\1 \2", cleaned)

    return cleaned.strip()


# ---------------------------------------------------------------------------
# Structure Extraction
# ---------------------------------------------------------------------------


def estimate_read_time(text: str) -> int:
    """Estimate reading time in minutes (assumes 200 words/minute).

    Args:
        text: Blog text content.

    Returns:
        Estimated minutes to read, minimum 1.
    """
    word_count = len(text.split())
    return max(1, round(word_count / 200))


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """Extract potential SEO keywords from the text.

    Uses simple frequency analysis with stop word filtering. Not a
    replacement for proper keyword research, but provides a starting point.

    Args:
        text: Full text content.
        max_keywords: Maximum keywords to return.

    Returns:
        List of keyword strings, most frequent first.
    """
    stop_words = {
        "the", "a", "an", "in", "to", "of", "and", "is", "for", "on", "it",
        "my", "i", "you", "your", "we", "our", "this", "that", "with", "from",
        "at", "by", "or", "not", "are", "was", "be", "but", "if", "so", "do",
        "has", "how", "what", "why", "when", "will", "can", "all", "just",
        "about", "its", "there", "been", "have", "they", "them", "their",
        "going", "get", "got", "really", "very", "also", "one", "two",
        "would", "could", "should", "here", "then", "than", "more", "some",
        "out", "into", "over", "these", "those", "lot", "know", "think",
        "see", "look", "want", "like", "make", "way", "come", "time",
    }

    # Extract 2-word and 3-word phrases
    words = re.findall(r"\b[a-z]+\b", text.lower())
    from collections import Counter

    # Single words (filtered)
    single = Counter(w for w in words if len(w) > 3 and w not in stop_words)

    # Bigrams
    bigrams = [
        f"{words[i]} {words[i+1]}"
        for i in range(len(words) - 1)
        if words[i] not in stop_words and words[i + 1] not in stop_words
        and len(words[i]) > 2 and len(words[i + 1]) > 2
    ]
    bigram_counts = Counter(bigrams)

    # Combine and rank
    keywords: list[str] = []
    # Prefer bigrams (more specific)
    for phrase, count in bigram_counts.most_common(max_keywords):
        if count >= 2:
            keywords.append(phrase)

    # Fill with single words
    for word, count in single.most_common(max_keywords * 2):
        if len(keywords) >= max_keywords:
            break
        if count >= 3 and not any(word in kw for kw in keywords):
            keywords.append(word)

    return keywords[:max_keywords]


def split_into_sections(text: str) -> list[dict]:
    """Split cleaned transcript text into logical sections.

    Uses sentence-level analysis to detect topic transitions based on
    discourse markers ("now", "so", "another thing", "moving on", etc.)
    and paragraph-length heuristics.

    Args:
        text: Cleaned transcript text.

    Returns:
        List of section dicts with 'type' and 'content' keys.
        Types: 'paragraph', 'subheading', 'callout', 'list'
    """
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return [{"type": "paragraph", "content": text}]

    # Topic transition markers
    transition_patterns = [
        r"^(now|so|okay|alright)\s*(let'?s|let me|i'?m going to|we'?re going to)",
        r"^(another|the next|next up|moving on)",
        r"^(first|second|third|fourth|fifth|finally|lastly)",
        r"^(one thing|the big|the main|the key|the important)",
        r"^(when it comes to|speaking of|as for|in terms of)",
        r"^(number \d|#\d|\d\.)",
    ]

    # Callout markers (tips, warnings, important notes)
    callout_patterns = [
        r"(pro tip|quick tip|here'?s a tip|one tip)",
        r"(important|keep in mind|don'?t forget|make sure|be aware)",
        r"(warning|watch out|careful|heads up)",
    ]

    sections: list[dict] = []
    current_paragraph: list[str] = []

    def flush_paragraph() -> None:
        """Save accumulated sentences as a paragraph."""
        if current_paragraph:
            content = " ".join(current_paragraph).strip()
            if content:
                sections.append({"type": "paragraph", "content": content})
            current_paragraph.clear()

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Check for callout
        is_callout = any(
            re.search(p, sentence, re.IGNORECASE) for p in callout_patterns
        )
        if is_callout:
            flush_paragraph()
            sections.append({"type": "callout", "content": sentence})
            continue

        # Check for topic transition → start new section with subheading
        is_transition = any(
            re.search(p, sentence, re.IGNORECASE) for p in transition_patterns
        )
        if is_transition and len(current_paragraph) >= 3:
            flush_paragraph()
            # The transition sentence hints at a new topic — use it as a
            # subheading seed (downstream agent can refine it)
            sections.append({"type": "subheading", "content": sentence})
            continue

        # Check for list-like content (e.g., "Number one: ...", "First, ...")
        if re.match(r"^(number \d|first|second|third|fourth|fifth|\d\.)", sentence, re.IGNORECASE):
            flush_paragraph()
            sections.append({"type": "list", "content": sentence})
            continue

        current_paragraph.append(sentence)

        # Auto-break long paragraphs (roughly every 4-6 sentences)
        if len(current_paragraph) >= 6:
            flush_paragraph()

    flush_paragraph()
    return sections


# ---------------------------------------------------------------------------
# Output Generation
# ---------------------------------------------------------------------------


def generate_blog_json(
    title: str,
    sections: list[dict],
    keywords: list[str],
    full_text: str,
    video_id: Optional[str],
    agent_name: Optional[str],
    style: str,
) -> dict:
    """Build the structured JSON blog template.

    Args:
        title: Blog post title.
        sections: List of section dicts from split_into_sections().
        keywords: Extracted SEO keywords.
        full_text: Full cleaned text for read time calculation.
        video_id: YouTube video ID (for embedding).
        agent_name: Author name.
        style: Writing style tag.

    Returns:
        Blog template dict ready for JSON serialization.
    """
    # Generate excerpt from first paragraph
    first_paragraph = next(
        (s["content"] for s in sections if s["type"] == "paragraph"), ""
    )
    excerpt = first_paragraph[:200].rsplit(" ", 1)[0] + "..." if len(first_paragraph) > 200 else first_paragraph

    # Generate meta description
    meta_desc = (
        first_paragraph[:155].rsplit(" ", 1)[0] + "..."
        if len(first_paragraph) > 155
        else first_paragraph
    )

    return {
        "title": title,
        "date": date.today().isoformat(),
        "author": agent_name or "Agent",
        "excerpt": excerpt,
        "metaDescription": meta_desc,
        "keywords": keywords,
        "readTime": estimate_read_time(full_text),
        "style": style,
        "youtubeId": video_id,
        "contentBlocks": sections,
    }


def generate_blog_markdown(
    title: str,
    sections: list[dict],
    keywords: list[str],
    full_text: str,
    video_id: Optional[str],
    agent_name: Optional[str],
) -> str:
    """Build a markdown blog post from structured sections.

    Includes YAML frontmatter compatible with most static site generators
    and CMS platforms.

    Args:
        title: Blog post title.
        sections: List of section dicts.
        keywords: SEO keywords for frontmatter tags.
        full_text: Full text for read time.
        video_id: YouTube video ID.
        agent_name: Author name.

    Returns:
        Complete markdown string with frontmatter.
    """
    # Frontmatter
    tags_str = "\n".join(f'  - "{kw}"' for kw in keywords[:6])
    first_paragraph = next(
        (s["content"] for s in sections if s["type"] == "paragraph"), ""
    )
    excerpt = first_paragraph[:200].rsplit(" ", 1)[0] + "..." if len(first_paragraph) > 200 else first_paragraph

    lines = [
        "---",
        f"title: \"{title}\"",
        f"date: {date.today().isoformat()}",
        f"author: \"{agent_name or 'Agent'}\"",
        f"excerpt: \"{excerpt}\"",
        f"readTime: {estimate_read_time(full_text)}",
        "tags:",
        tags_str,
    ]
    if video_id:
        lines.append(f"youtubeId: \"{video_id}\"")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")

    # YouTube embed placeholder
    if video_id:
        lines.append(
            f"{{{{< youtube id=\"{video_id}\" >}}}}"
        )
        lines.append("")

    # Content sections
    subheading_count = 0
    for section in sections:
        stype = section["type"]
        content = section["content"]

        if stype == "subheading":
            subheading_count += 1
            # Use content as a heading seed — clean it up
            heading = content.strip().rstrip(".")
            if len(heading) > 80:
                heading = heading[:77] + "..."
            lines.append(f"## {heading}")
            lines.append("")
        elif stype == "paragraph":
            lines.append(content)
            lines.append("")
        elif stype == "callout":
            lines.append(f"> **Note:** {content}")
            lines.append("")
        elif stype == "list":
            lines.append(f"- {content}")
            # Don't add blank line between consecutive list items
        else:
            lines.append(content)
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a YouTube transcript into a structured blog post.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  python3 transcript_to_blog.py video_abc123.txt --title "Best Neighborhoods in St. Pete"

  # Full options
  python3 transcript_to_blog.py video_abc123.txt \\
      --title "Best Neighborhoods in St. Pete" \\
      --agent-name "Aaron Chand" \\
      --style conversational \\
      --output blog.md

  # Just generate JSON structure
  python3 transcript_to_blog.py video_abc123.txt --title "My Video" --json-only
        """,
    )

    parser.add_argument(
        "transcript_file",
        type=Path,
        help="Path to the transcript .txt file",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Blog post title (defaults to filename)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path for markdown (default: <transcript_stem>_blog.md)",
    )
    parser.add_argument(
        "--style",
        type=str,
        default="conversational",
        choices=["conversational", "professional", "educational", "listicle"],
        help="Writing style tag (default: conversational)",
    )
    parser.add_argument(
        "--agent-name",
        type=str,
        default=None,
        help="Author name for the blog post",
    )
    parser.add_argument(
        "--video-id",
        type=str,
        default=None,
        help="YouTube video ID for embedding (auto-detected from filename if possible)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only output the JSON structure (no markdown)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.transcript_file.exists():
        print(f"ERROR: File not found: {args.transcript_file}", file=sys.stderr)
        sys.exit(1)

    # Read transcript
    raw_text = args.transcript_file.read_text(encoding="utf-8")
    if not raw_text.strip():
        print("ERROR: Transcript file is empty.", file=sys.stderr)
        sys.exit(1)

    # Determine title
    title = args.title or args.transcript_file.stem.replace("_", " ").replace("-", " ").title()

    # Auto-detect video ID from filename (common pattern: VIDEO_ID.txt)
    video_id = args.video_id
    if not video_id:
        stem = args.transcript_file.stem
        # YouTube video IDs are 11 characters, alphanumeric + _ and -
        if re.match(r"^[A-Za-z0-9_-]{11}$", stem):
            video_id = stem

    # Process
    print(f"Processing: {args.transcript_file.name}")
    print(f"  Title: {title}")
    print(f"  Raw length: {len(raw_text):,} chars")

    # Step 1: Clean
    cleaned = clean_transcript(raw_text)
    print(f"  Cleaned length: {len(cleaned):,} chars")

    # Step 2: Extract keywords
    keywords = extract_keywords(cleaned)
    print(f"  Keywords: {', '.join(keywords[:5])}...")

    # Step 3: Split into sections
    sections = split_into_sections(cleaned)
    section_types = {}
    for s in sections:
        section_types[s["type"]] = section_types.get(s["type"], 0) + 1
    print(f"  Sections: {dict(section_types)}")

    # Step 4: Generate outputs
    blog_json = generate_blog_json(
        title=title,
        sections=sections,
        keywords=keywords,
        full_text=cleaned,
        video_id=video_id,
        agent_name=args.agent_name,
        style=args.style,
    )

    # Save JSON
    json_path = args.transcript_file.with_name(
        args.transcript_file.stem + "_blog.json"
    )
    json_path.write_text(
        json.dumps(blog_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  JSON saved: {json_path}")

    # Save markdown (unless --json-only)
    if not args.json_only:
        md_content = generate_blog_markdown(
            title=title,
            sections=sections,
            keywords=keywords,
            full_text=cleaned,
            video_id=video_id,
            agent_name=args.agent_name,
        )

        md_path = args.output or args.transcript_file.with_name(
            args.transcript_file.stem + "_blog.md"
        )
        md_path.write_text(md_content, encoding="utf-8")
        print(f"  Markdown saved: {md_path}")
        print(f"  Read time: ~{blog_json['readTime']} min")


if __name__ == "__main__":
    main()
