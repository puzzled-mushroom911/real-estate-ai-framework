#!/usr/bin/env python3
"""
Fetch YouTube Video Metadata & Transcripts via yt-dlp

Downloads recent video metadata and auto-generated transcripts from one or more
YouTube channels. Saves individual transcript .txt files and metadata .json files
for downstream processing (RAG ingestion, blog generation, etc.).

Dependencies:
    - yt-dlp (brew install yt-dlp)

Usage:
    # Single channel
    python3 fetch_videos.py --channel "@ChannelHandle" --days 60 --max 20

    # Multiple channels from YAML config
    python3 fetch_videos.py --channels-file channels.yaml --days 30

    # Dry run (show what would be fetched without downloading)
    python3 fetch_videos.py --channel "@ChannelHandle" --dry-run
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# VTT → Plaintext Conversion
# ---------------------------------------------------------------------------


def vtt_to_plaintext(vtt_text: str) -> str:
    """Convert WebVTT subtitle content to clean plaintext.

    Strips all VTT formatting: headers, timestamps, cue identifiers, HTML tags,
    and deduplicates consecutive identical lines (common in auto-generated subs
    where lines repeat for scrolling display).

    Args:
        vtt_text: Raw contents of a .vtt subtitle file.

    Returns:
        Clean plaintext string with all speech content joined.
    """
    lines = vtt_text.strip().split("\n")
    text_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip WEBVTT header, NOTE blocks, and metadata lines
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        # Skip timestamp lines (e.g., "00:00:01.440 --> 00:00:04.320")
        if "-->" in line:
            continue
        # Skip numeric cue identifiers
        if re.match(r"^\d+$", line):
            continue
        # Strip inline VTT tags: <c>, </c>, <00:00:01.440>, position/align attrs
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line:
            text_lines.append(line)

    # Deduplicate consecutive identical lines
    deduped: list[str] = []
    for line in text_lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    # Join and normalize whitespace
    raw = " ".join(deduped)
    return re.sub(r"\s+", " ", raw).strip()


# ---------------------------------------------------------------------------
# yt-dlp Helpers
# ---------------------------------------------------------------------------


def _check_ytdlp() -> None:
    """Verify yt-dlp is installed, exit with helpful message if not."""
    try:
        subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        print(
            "ERROR: yt-dlp not found.\n"
            "  Install with: brew install yt-dlp  (macOS)\n"
            "            or: pip install yt-dlp",
            file=sys.stderr,
        )
        sys.exit(1)


def fetch_channel_videos(
    handle: str,
    max_videos: int = 20,
    days: int = 60,
) -> list[dict]:
    """Fetch recent video metadata from a YouTube channel.

    Uses yt-dlp --dump-json with --flat-playlist for fast metadata retrieval.
    Filters results to only include videos within the specified time window.

    Args:
        handle: YouTube channel handle (e.g., "@ChannelHandle").
        max_videos: Maximum number of videos to return.
        days: Only include videos uploaded within this many days.

    Returns:
        List of video metadata dicts, newest first.
    """
    url = f"https://www.youtube.com/{handle}/videos"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        f"--playlist-end={max_videos * 2}",  # Fetch extra; we filter by date
        "--no-warnings",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"  WARNING: yt-dlp timed out for {handle}", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(
            f"  WARNING: yt-dlp error for {handle}: {result.stderr[:300]}",
            file=sys.stderr,
        )
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    videos: list[dict] = []

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        video_id = data.get("id", "")
        if not video_id:
            continue

        # Parse upload date (YYYYMMDD format)
        upload_date_str = data.get("upload_date", "")
        upload_date: Optional[datetime] = None
        if upload_date_str and len(upload_date_str) == 8:
            try:
                upload_date = datetime.strptime(upload_date_str, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        # Skip videos older than our cutoff
        if upload_date and upload_date < cutoff:
            continue

        videos.append(
            {
                "id": video_id,
                "title": data.get("title", "Untitled"),
                "url": (
                    data.get("url")
                    or data.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={video_id}"
                ),
                "upload_date": upload_date_str,
                "view_count": data.get("view_count", 0) or 0,
                "duration": data.get("duration", 0) or 0,
                "description": data.get("description", ""),
                "channel_name": data.get("channel", data.get("uploader", "")),
                "channel_id": data.get("channel_id", data.get("uploader_id", "")),
            }
        )

    return videos[:max_videos]


def fetch_full_metadata(video_id: str) -> Optional[dict]:
    """Fetch complete metadata for a single video.

    The flat-playlist mode returns limited metadata. This function fetches
    the full metadata dump for a specific video, which includes duration,
    description, like count, etc.

    Args:
        video_id: YouTube video ID.

    Returns:
        Full metadata dict, or None on failure.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
        "--skip-download",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def download_subtitles(video_id: str, output_dir: Path) -> Optional[Path]:
    """Download auto-generated subtitles for a video.

    Args:
        video_id: YouTube video ID.
        output_dir: Directory to save the VTT file.

    Returns:
        Path to the downloaded VTT file, or None if unavailable.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = str(output_dir / f"{video_id}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--write-auto-subs",
        "--sub-langs=en.*",
        "--sub-format=vtt",
        "--skip-download",
        "--no-warnings",
        f"--output={output_template}",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None

    # Find the downloaded VTT file (yt-dlp appends language suffix)
    for vtt_file in output_dir.glob(f"{video_id}*.vtt"):
        return vtt_file
    return None


# ---------------------------------------------------------------------------
# Channel Config (YAML)
# ---------------------------------------------------------------------------


def load_channels_file(path: Path) -> list[dict]:
    """Load a channels YAML config file.

    Expected format:
        channels:
          - handle: "@ChannelHandle"
            name: "Display Name"
            category: "competitor"  # optional

    Falls back to a simple list format:
        - handle: "@ChannelHandle"
          name: "Display Name"

    Args:
        path: Path to the YAML file.

    Returns:
        List of channel config dicts.
    """
    try:
        import yaml
    except ImportError:
        print(
            "ERROR: PyYAML required for --channels-file.\n"
            "  Install with: pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Support both {channels: [...]} and bare [...]
    if isinstance(raw, dict) and "channels" in raw:
        channels = raw["channels"]
    elif isinstance(raw, list):
        channels = raw
    else:
        print(f"ERROR: Unexpected format in {path}", file=sys.stderr)
        sys.exit(1)

    # Validate each entry has at least a handle
    validated: list[dict] = []
    for entry in channels:
        if not isinstance(entry, dict) or "handle" not in entry:
            print(f"  WARNING: Skipping invalid entry: {entry}", file=sys.stderr)
            continue
        validated.append(
            {
                "handle": entry["handle"],
                "name": entry.get("name", entry["handle"]),
                "category": entry.get("category", ""),
            }
        )
    return validated


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def format_date(yyyymmdd: str) -> str:
    """Convert YYYYMMDD string to ISO 8601 date string."""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return yyyymmdd
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return yyyymmdd


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration (HH:MM:SS or MM:SS)."""
    if not seconds:
        return "0:00"
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# Processing Pipeline
# ---------------------------------------------------------------------------


def process_channel(
    handle: str,
    name: str,
    output_dir: Path,
    days: int,
    max_videos: int,
    dry_run: bool,
) -> dict:
    """Process a single channel: fetch metadata, download transcripts.

    For each video found:
      1. Saves metadata to <output_dir>/<video_id>.json
      2. Downloads auto-generated subtitles
      3. Converts VTT to plaintext, saves to <output_dir>/<video_id>.txt

    Args:
        handle: YouTube channel handle.
        name: Display name for logging.
        output_dir: Directory to save transcripts and metadata.
        days: Look-back window in days.
        max_videos: Maximum videos to fetch.
        dry_run: If True, only show what would be fetched.

    Returns:
        Summary dict with counts and any errors.
    """
    print(f"\n{'=' * 60}")
    print(f"Channel: {name} ({handle})")
    print(f"{'=' * 60}")

    result = {
        "channel": name,
        "handle": handle,
        "videos_found": 0,
        "transcripts_downloaded": 0,
        "errors": [],
    }

    # Fetch video list
    print(f"  Scanning for videos from last {days} days (max {max_videos})...")
    videos = fetch_channel_videos(handle, max_videos=max_videos, days=days)
    result["videos_found"] = len(videos)
    print(f"  Found {len(videos)} videos")

    if not videos:
        return result

    # In dry-run mode, just list the videos
    if dry_run:
        print("\n  [DRY RUN] Would download transcripts for:")
        for v in videos:
            date_str = format_date(v.get("upload_date", ""))
            duration_str = format_duration(v.get("duration", 0))
            views = v.get("view_count", 0)
            print(f"    - {v['title'][:60]}")
            print(f"      {date_str} | {duration_str} | {views:,} views")
        return result

    # Create channel output subdirectory
    channel_dir = output_dir / handle.lstrip("@")
    channel_dir.mkdir(parents=True, exist_ok=True)

    for v in videos:
        video_id = v["id"]
        print(f"\n  Processing: {v['title'][:55]}...")

        # Fetch full metadata if flat-playlist gave us incomplete data
        if not v.get("duration") or not v.get("description"):
            full_meta = fetch_full_metadata(video_id)
            if full_meta:
                v["duration"] = full_meta.get("duration", v.get("duration", 0))
                v["description"] = full_meta.get(
                    "description", v.get("description", "")
                )
                v["view_count"] = full_meta.get(
                    "view_count", v.get("view_count", 0)
                )
                v["channel_name"] = full_meta.get(
                    "channel", v.get("channel_name", "")
                )
                v["channel_id"] = full_meta.get(
                    "channel_id", v.get("channel_id", "")
                )

        # Save metadata JSON
        meta_path = channel_dir / f"{video_id}.json"
        meta_payload = {
            "video_id": video_id,
            "title": v.get("title", "Untitled"),
            "url": v.get("url", f"https://www.youtube.com/watch?v={video_id}"),
            "upload_date": format_date(v.get("upload_date", "")),
            "duration_seconds": v.get("duration", 0),
            "duration_display": format_duration(v.get("duration", 0)),
            "view_count": v.get("view_count", 0),
            "description": v.get("description", ""),
            "channel_name": v.get("channel_name", name),
            "channel_handle": handle,
            "channel_id": v.get("channel_id", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(
            json.dumps(meta_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"    Metadata saved: {meta_path.name}")

        # Download subtitles and convert to plaintext
        vtt_path = download_subtitles(video_id, channel_dir)
        if vtt_path:
            try:
                vtt_text = vtt_path.read_text(encoding="utf-8")
                transcript = vtt_to_plaintext(vtt_text)

                if transcript:
                    txt_path = channel_dir / f"{video_id}.txt"
                    txt_path.write_text(transcript, encoding="utf-8")
                    result["transcripts_downloaded"] += 1
                    print(
                        f"    Transcript saved: {txt_path.name} "
                        f"({len(transcript):,} chars)"
                    )

                    # Clean up the raw VTT file to save space
                    vtt_path.unlink(missing_ok=True)
                else:
                    print("    WARNING: Empty transcript after VTT parsing")
                    result["errors"].append(
                        f"{video_id}: Empty transcript after parsing"
                    )
            except Exception as e:
                print(f"    WARNING: Error processing VTT: {e}")
                result["errors"].append(f"{video_id}: VTT processing error: {e}")
        else:
            print("    WARNING: No subtitles available for this video")
            result["errors"].append(f"{video_id}: No subtitles available")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download YouTube video metadata and transcripts via yt-dlp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch last 60 days from a single channel
  python3 fetch_videos.py --channel "@ChannelHandle" --days 60 --max 20

  # Process multiple channels from a YAML config
  python3 fetch_videos.py --channels-file channels.yaml

  # Preview without downloading
  python3 fetch_videos.py --channel "@ChannelHandle" --dry-run

channels.yaml format:
  channels:
    - handle: "@ChannelHandle"
      name: "Display Name"
      category: "own_channel"
    - handle: "@CompetitorHandle"
      name: "Competitor Name"
      category: "competitor"
        """,
    )

    # Channel source (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--channel",
        type=str,
        help='YouTube channel handle (e.g., "@ChannelHandle")',
    )
    source_group.add_argument(
        "--channels-file",
        type=Path,
        help="Path to a YAML file listing multiple channels",
    )

    # Filtering options
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Look back this many days for recent videos (default: 60)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=20,
        dest="max_videos",
        help="Maximum videos to fetch per channel (default: 20)",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./transcripts"),
        help="Directory to save transcripts and metadata (default: ./transcripts)",
    )

    # Behavior
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without downloading anything",
    )

    args = parser.parse_args()

    # Verify yt-dlp is installed
    _check_ytdlp()

    # Build channel list
    channels: list[dict] = []
    if args.channel:
        channels = [{"handle": args.channel, "name": args.channel, "category": ""}]
    else:
        if not args.channels_file.exists():
            print(f"ERROR: Channels file not found: {args.channels_file}", file=sys.stderr)
            sys.exit(1)
        channels = load_channels_file(args.channels_file)
        if not channels:
            print("ERROR: No valid channels found in config file", file=sys.stderr)
            sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process each channel
    all_results: list[dict] = []
    for ch in channels:
        channel_result = process_channel(
            handle=ch["handle"],
            name=ch["name"],
            output_dir=args.output_dir,
            days=args.days,
            max_videos=args.max_videos,
            dry_run=args.dry_run,
        )
        all_results.append(channel_result)

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    total_videos = sum(r["videos_found"] for r in all_results)
    total_transcripts = sum(r["transcripts_downloaded"] for r in all_results)
    total_errors = sum(len(r["errors"]) for r in all_results)

    print(f"  Channels processed:    {len(all_results)}")
    print(f"  Videos found:          {total_videos}")
    if not args.dry_run:
        print(f"  Transcripts saved:     {total_transcripts}")
    if total_errors:
        print(f"  Errors:                {total_errors}")
    print(f"  Output directory:      {args.output_dir.resolve()}")

    # Save run summary as JSON
    if not args.dry_run:
        summary_path = args.output_dir / "_fetch_summary.json"
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "params": {
                "days": args.days,
                "max_videos": args.max_videos,
                "dry_run": args.dry_run,
            },
            "results": all_results,
        }
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  Summary saved:         {summary_path.name}")


if __name__ == "__main__":
    main()
