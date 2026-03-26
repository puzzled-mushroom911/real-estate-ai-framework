#!/usr/bin/env python3
"""
Generate Email Sequence Templates from Video Content

Reads a transcript .txt file or structured blog .json file and extracts
content elements (stories, data points, insights, questions) suitable for
email marketing. Outputs a JSON template with email skeletons designed
to be fed to an AI email-writer agent for final copy production.

The output is intentionally a TEMPLATE — it provides the raw material
(story seeds, data points, CTAs) so the email-writing agent can craft
the final copy in the agent's voice.

Dependencies:
    - None (stdlib only)

Usage:
    # From a transcript
    python3 generate_emails.py transcript.txt --sequence-type nurture --count 5

    # From a blog JSON
    python3 generate_emails.py blog.json --sequence-type welcome --count 3

    # Custom output directory
    python3 generate_emails.py transcript.txt --output ./emails/
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Content Extraction
# ---------------------------------------------------------------------------


def extract_stories(text: str) -> list[dict]:
    """Extract narrative / anecdotal segments from transcript text.

    Looks for first-person narrative patterns that indicate personal stories,
    client examples, or experiential content — the kind of material that
    makes compelling email content.

    Args:
        text: Cleaned transcript or blog text.

    Returns:
        List of dicts with 'text' (the story excerpt) and 'type' (story category).
    """
    story_patterns = [
        # Personal experience markers
        (r"(I remember[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "personal_experience"),
        (r"(When I first[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "personal_experience"),
        (r"(I actually[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "personal_experience"),
        (r"(We had a client[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "client_story"),
        (r"(One of (?:my|our) (?:clients?|buyers?)[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "client_story"),
        (r"(I worked with[^.!?]*[.!?](?:\s+[^.!?]*[.!?])?)", "client_story"),
        # Surprise / insight markers
        (r"(What (?:most people|a lot of people|many people) don'?t (?:know|realize)[^.!?]*[.!?])", "insight"),
        (r"(The (?:crazy|interesting|surprising|wild) thing is[^.!?]*[.!?])", "insight"),
        (r"(Here'?s (?:what|the thing)[^.!?]*[.!?])", "insight"),
    ]

    stories: list[dict] = []
    seen_starts: set[str] = set()

    for pattern, story_type in story_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Deduplicate by first 50 chars
            start = match[:50]
            if start not in seen_starts and len(match) > 30:
                seen_starts.add(start)
                stories.append({"text": match.strip(), "type": story_type})

    return stories


def extract_data_points(text: str) -> list[dict]:
    """Extract statistics, numbers, and factual claims from the text.

    Finds sentences containing specific data (dollar amounts, percentages,
    year references, quantities) that can serve as credibility anchors
    in email content.

    Args:
        text: Cleaned transcript or blog text.

    Returns:
        List of dicts with 'text' and 'data_type'.
    """
    data_patterns = [
        (r"([^.!?]*\$[\d,]+[^.!?]*[.!?])", "dollar_amount"),
        (r"([^.!?]*\d+(?:\.\d+)?%[^.!?]*[.!?])", "percentage"),
        (r"([^.!?]*(?:median|average|typical)\s+(?:home|house|price|rent|income)[^.!?]*[.!?])", "market_stat"),
        (r"([^.!?]*(?:population|residents|people)\s+(?:of|is|are|was)\s+[\d,]+[^.!?]*[.!?])", "demographic"),
        (r"([^.!?]*(?:ranked|rated|scored|#\d)\s[^.!?]*[.!?])", "ranking"),
    ]

    data_points: list[dict] = []
    seen: set[str] = set()

    for pattern, dtype in data_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            trimmed = match.strip()
            key = trimmed[:60]
            if key not in seen and len(trimmed) > 20:
                seen.add(key)
                data_points.append({"text": trimmed, "data_type": dtype})

    return data_points


def extract_insights(text: str) -> list[str]:
    """Extract actionable insights and advice from the text.

    Targets sentences with advisory language (should, need to, make sure,
    tip, advice) that represent the agent's expertise.

    Args:
        text: Cleaned transcript or blog text.

    Returns:
        List of insight strings.
    """
    insight_patterns = [
        r"([^.!?]*(?:you (?:should|need to|want to|have to))[^.!?]*[.!?])",
        r"([^.!?]*(?:make sure|be sure|don'?t forget)[^.!?]*[.!?])",
        r"([^.!?]*(?:my (?:advice|recommendation|tip))[^.!?]*[.!?])",
        r"([^.!?]*(?:the (?:key|trick|secret) (?:is|to))[^.!?]*[.!?])",
        r"([^.!?]*(?:biggest mistake|common mistake|avoid)[^.!?]*[.!?])",
        r"([^.!?]*(?:pro tip|here'?s a tip|quick tip)[^.!?]*[.!?])",
    ]

    insights: list[str] = []
    seen: set[str] = set()

    for pattern in insight_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            trimmed = match.strip()
            key = trimmed[:50]
            if key not in seen and len(trimmed) > 25:
                seen.add(key)
                insights.append(trimmed)

    return insights


def extract_questions(text: str) -> list[str]:
    """Extract questions from the text that could drive email engagement.

    Questions in video content often mirror what the audience is thinking,
    making them effective email subject lines or conversation starters.

    Args:
        text: Cleaned transcript or blog text.

    Returns:
        List of question strings.
    """
    # Find sentences ending in "?"
    questions = re.findall(r"([^.!?]*\?)", text)
    # Filter out very short or very long questions
    filtered = [
        q.strip()
        for q in questions
        if 15 < len(q.strip()) < 200
    ]
    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for q in filtered:
        key = q[:40]
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


# ---------------------------------------------------------------------------
# Email Template Generation
# ---------------------------------------------------------------------------


def generate_email_templates(
    title: str,
    stories: list[dict],
    data_points: list[dict],
    insights: list[str],
    questions: list[str],
    sequence_type: str,
    count: int,
    agent_name: Optional[str],
) -> list[dict]:
    """Build email skeleton templates from extracted content elements.

    Each template provides raw material for an email-writer agent:
    subject line options, an opening hook seed, a story seed, a pivot
    point concept, CTA options, and a P.S. line option.

    Args:
        title: Source content title.
        stories: Extracted story/anecdote dicts.
        data_points: Extracted data point dicts.
        insights: Extracted insight strings.
        questions: Extracted questions.
        sequence_type: Type of sequence (nurture, welcome, weekly).
        count: Number of email templates to generate.
        agent_name: Agent name for personalization.

    Returns:
        List of email template dicts.
    """
    templates: list[dict] = []
    name = agent_name or "Agent"

    # Define sequence-specific patterns
    sequence_patterns = {
        "nurture": {
            "cadence": "every 3-5 days",
            "goal": "build trust and demonstrate local expertise",
            "cta_styles": ["soft_ask", "value_offer", "question", "resource"],
        },
        "welcome": {
            "cadence": "daily for first 3, then every 2-3 days",
            "goal": "introduce yourself and establish credibility fast",
            "cta_styles": ["introduce", "value_offer", "social_proof", "booking"],
        },
        "weekly": {
            "cadence": "weekly",
            "goal": "stay top of mind with fresh market insights",
            "cta_styles": ["market_update", "new_content", "question", "booking"],
        },
    }

    pattern = sequence_patterns.get(sequence_type, sequence_patterns["nurture"])

    for i in range(count):
        email: dict = {
            "email_number": i + 1,
            "sequence_type": sequence_type,
            "cadence": pattern["cadence"],
            "goal": pattern["goal"],
            "source_content": title,
        }

        # Subject line options — draw from questions, data points, insights
        subject_options: list[str] = []

        # Option 1: Question-based subject
        if questions and i < len(questions):
            q = questions[i % len(questions)]
            subject_options.append(q[:70])
        else:
            subject_options.append(f"What nobody tells you about relocating")

        # Option 2: Data-driven subject
        if data_points and i < len(data_points):
            dp = data_points[i % len(data_points)]
            # Shorten to subject-line length
            dp_text = dp["text"][:65]
            if len(dp["text"]) > 65:
                dp_text = dp_text.rsplit(" ", 1)[0] + "..."
            subject_options.append(dp_text)
        else:
            subject_options.append(f"A quick {title.lower()[:40]} insight")

        # Option 3: Story teaser
        if stories and i < len(stories):
            s = stories[i % len(stories)]
            teaser = s["text"][:60]
            if len(s["text"]) > 60:
                teaser = teaser.rsplit(" ", 1)[0] + "..."
            subject_options.append(teaser)
        else:
            subject_options.append(f"{name} here — got a minute?")

        email["subject_line_options"] = subject_options

        # Opening hook — rotate approaches
        hooks = [
            f"Quick question for you...",
            f"I was talking to a buyer last week and something came up that I think you need to hear.",
            f"If you're thinking about making a move, this one thing could save you a lot of headaches.",
            f"Real talk — most people get this wrong when relocating.",
            f"I see this mistake all the time, and it costs people thousands.",
        ]
        email["opening_hook"] = hooks[i % len(hooks)]

        # Story seed — the raw material for the email body
        if stories:
            story = stories[i % len(stories)]
            email["story_seed"] = {
                "raw_text": story["text"],
                "type": story["type"],
                "instruction": (
                    f"Expand this {story['type'].replace('_', ' ')} into "
                    f"2-3 paragraphs in {name}'s voice. Keep it conversational "
                    f"and relatable. End with a natural pivot to the CTA."
                ),
            }
        else:
            # Fall back to an insight if no stories available
            insight_text = insights[i % len(insights)] if insights else title
            email["story_seed"] = {
                "raw_text": insight_text,
                "type": "insight",
                "instruction": (
                    f"Build a brief narrative around this insight. "
                    f"Use {name}'s conversational voice. 2-3 paragraphs max."
                ),
            }

        # Pivot point — the transition from story to CTA
        pivots = [
            "This is exactly why having a local agent matters.",
            "And that's something I help my buyers navigate every day.",
            "I put together something that covers this in detail.",
            "If this resonates with you, I'd love to chat about your situation.",
            "This is one of the things I walk all my buyers through.",
        ]
        email["pivot_point"] = pivots[i % len(pivots)]

        # CTA options — matched to sequence type
        cta_style = pattern["cta_styles"][i % len(pattern["cta_styles"])]
        cta_map = {
            "soft_ask": [
                "Hit reply and tell me — what's your biggest concern about relocating?",
                "Reply back if you want me to send you more details on this.",
            ],
            "value_offer": [
                "I put together a free relocation guide that covers all of this. Want me to send it over?",
                f"I've got a detailed breakdown of [topic]. Reply 'YES' and I'll send it your way.",
            ],
            "question": [
                "What's the #1 thing you want to know about [area]? Hit reply — I read every one.",
                "Are you looking in a specific area? I can give you the real scoop.",
            ],
            "resource": [
                "Check out this video where I walk through everything: [VIDEO_LINK]",
                "I covered this in depth on my YouTube channel — here's the link: [VIDEO_LINK]",
            ],
            "introduce": [
                f"I'm {name}, and I help buyers relocate to [area]. Reply and tell me about your timeline.",
                f"Want to get on a quick call? Here's my calendar: [BOOKING_LINK]",
            ],
            "social_proof": [
                "I've helped over 50 buyers make this move. Let me know if you want to be next.",
                "One of my recent buyers said this was the most helpful thing they read. Reply if you want similar insights.",
            ],
            "booking": [
                "Ready to talk specifics? Grab a time on my calendar: [BOOKING_LINK]",
                "Let's hop on a quick 15-min call. No pressure, just answers: [BOOKING_LINK]",
            ],
            "market_update": [
                "Want a personalized market snapshot for the area you're looking at? Just reply with the neighborhood.",
                "I send these updates every week. Reply 'KEEP' if you want to stay on the list.",
            ],
            "new_content": [
                "I just dropped a new video on [topic] — check it out: [VIDEO_LINK]",
                "New blog post is up: [BLOG_LINK]. Let me know what you think.",
            ],
        }
        email["cta_options"] = cta_map.get(cta_style, cta_map["soft_ask"])

        # P.S. line — always include one; high readership spot
        ps_options = [
            f"P.S. If you know someone else thinking about relocating, forward this to them. I'm happy to help.",
            f"P.S. I post new videos every week on my YouTube channel. Subscribe so you don't miss anything.",
            f"P.S. Fun fact — {data_points[i % len(data_points)]['text'][:80]}..." if data_points else f"P.S. Hit reply with any questions. I read and respond to every single one.",
        ]
        email["ps_line"] = ps_options[i % len(ps_options)]

        # Supporting data points for this email
        if data_points:
            dp_start = (i * 2) % len(data_points)
            email["supporting_data"] = [
                dp["text"]
                for dp in data_points[dp_start : dp_start + 2]
            ]
        else:
            email["supporting_data"] = []

        templates.append(email)

    return templates


# ---------------------------------------------------------------------------
# Input Parsing
# ---------------------------------------------------------------------------


def load_input(file_path: Path) -> tuple[str, str]:
    """Load input from either a .txt transcript or a .json blog file.

    Args:
        file_path: Path to the input file.

    Returns:
        Tuple of (title, full_text).
    """
    suffix = file_path.suffix.lower()

    if suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        title = data.get("title", file_path.stem)
        # Reconstruct text from content blocks
        blocks = data.get("contentBlocks", data.get("content_blocks", []))
        if blocks:
            text_parts = [b.get("content", "") for b in blocks]
            return title, " ".join(text_parts)
        # Fallback: look for a text field
        return title, data.get("content", data.get("text", ""))

    # Default: treat as plain text
    text = file_path.read_text(encoding="utf-8").strip()
    title = file_path.stem.replace("_", " ").replace("-", " ").title()
    return title, text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate email sequence templates from video/blog content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 5-email nurture sequence from a transcript
  python3 generate_emails.py transcript.txt --sequence-type nurture --count 5

  # 3-email welcome sequence from a blog JSON
  python3 generate_emails.py blog.json --sequence-type welcome --count 3

  # Custom output
  python3 generate_emails.py transcript.txt --output ./emails/ --agent-name "Aaron Chand"
        """,
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to a transcript .txt file or blog .json file",
    )
    parser.add_argument(
        "--sequence-type",
        type=str,
        default="nurture",
        choices=["nurture", "welcome", "weekly"],
        help="Type of email sequence (default: nurture)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of emails in the sequence (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for email templates (default: same dir as input)",
    )
    parser.add_argument(
        "--agent-name",
        type=str,
        default=None,
        help="Agent name for personalization in templates",
    )

    args = parser.parse_args()

    # Validate input
    if not args.input_file.exists():
        print(f"ERROR: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Load content
    title, text = load_input(args.input_file)
    if not text.strip():
        print("ERROR: Input file contains no text content.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing: {args.input_file.name}")
    print(f"  Title: {title}")
    print(f"  Content length: {len(text):,} chars")
    print(f"  Sequence type: {args.sequence_type}")
    print(f"  Email count: {args.count}")

    # Extract content elements
    stories = extract_stories(text)
    data_points = extract_data_points(text)
    insights = extract_insights(text)
    questions = extract_questions(text)

    print(f"\n  Extracted content elements:")
    print(f"    Stories/anecdotes:  {len(stories)}")
    print(f"    Data points:       {len(data_points)}")
    print(f"    Insights/advice:   {len(insights)}")
    print(f"    Questions:         {len(questions)}")

    # Generate templates
    templates = generate_email_templates(
        title=title,
        stories=stories,
        data_points=data_points,
        insights=insights,
        questions=questions,
        sequence_type=args.sequence_type,
        count=args.count,
        agent_name=args.agent_name,
    )

    # Build output
    output_data = {
        "sequence_type": args.sequence_type,
        "source_content": title,
        "agent_name": args.agent_name or "Agent",
        "generated_date": date.today().isoformat(),
        "email_count": len(templates),
        "extracted_elements": {
            "stories": len(stories),
            "data_points": len(data_points),
            "insights": len(insights),
            "questions": len(questions),
        },
        "emails": templates,
        "raw_elements": {
            "stories": stories[:10],
            "data_points": data_points[:10],
            "insights": insights[:10],
            "questions": questions[:10],
        },
    }

    # Save output
    output_dir = args.output or args.input_file.parent
    if args.output:
        output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{args.input_file.stem}_{args.sequence_type}_emails.json"
    output_file.write_text(
        json.dumps(output_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n  Output saved: {output_file}")
    print(f"\n  Email template summary:")
    for tmpl in templates:
        print(f"    Email {tmpl['email_number']}: {tmpl['subject_line_options'][0][:55]}...")

    print(f"\n  Next step: Feed this JSON to your email-writer agent for final copy.")


if __name__ == "__main__":
    main()
