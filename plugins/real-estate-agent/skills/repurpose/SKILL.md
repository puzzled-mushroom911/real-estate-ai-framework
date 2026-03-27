---
name: repurpose
description: Repurpose a YouTube video or transcript into blog posts, emails, social media posts, and lead magnets. Use when asked to repurpose content, turn a video into a blog, create social posts from a transcript, or generate emails from video content.
---

# Content Repurposer

Take a single piece of content (YouTube video, transcript, or voice note) and turn it into multiple formats -- all in the agent's authentic voice.

## Process

1. **Get the source content:**
   - If the user provides a YouTube URL, extract the transcript:
     ```bash
     yt-dlp --write-auto-sub --sub-lang en --skip-download -o "%(title)s" "<URL>"
     ```
   - If the user pastes a transcript or drags in a file, use that directly
   - If the user says "my latest video" or similar, check the agent's YouTube channel config in `<PLUGIN_ROOT>/config/channels.yaml` and pull the most recent

2. **Analyze the source:**
   - Identify the main topic, key points, and memorable quotes
   - Note the agent's tone, phrasing patterns, and unique perspectives
   - Extract specific data points, statistics, or examples mentioned
   - Identify the strongest 2-3 soundbites for social media

3. **Ask what formats they want** (or do all if they say "everything"):

   - **Blog post** -- SEO-optimized, 1200-1800 words, maintains the agent's voice
   - **Email sequence** (3 emails) -- Seinfeld-style storytelling that nurtures leads
   - **Social media posts** (5 posts) -- Platform-appropriate (Instagram captions, Twitter threads, Facebook posts)
   - **YouTube Shorts script** (3 scripts) -- 30-60 second scripts from the best moments
   - **Lead magnet excerpt** -- A downloadable one-pager or checklist extracted from the content

4. **Generate each format:**
   - Always maintain the agent's voice -- never sound generic
   - Include the agent's credential line where natural
   - End each piece with an appropriate CTA and booking link
   - Blog posts should use the agent's website URL for internal linking
   - All content must be Fair Housing compliant

## Output Format

Deliver each piece clearly labeled and ready to copy-paste:

```
## Repurposed Content: [Original Title]
**Source:** [YouTube URL or filename]
**Date:** [YYYY-MM-DD]

---

### 1. Blog Post
[Full blog post in markdown]

### 2. Email Sequence
**Email 1:** [Subject line]
[Body]

**Email 2:** [Subject line]
[Body]

**Email 3:** [Subject line]
[Body]

### 3. Social Media Posts
**Instagram:** [Caption with hashtags]
**Twitter/X:** [Thread or single post]
**Facebook:** [Post with engagement prompt]

### 4. YouTube Shorts Scripts
**Short 1:** [Title]
[Script with timing notes]

### 5. Lead Magnet Excerpt
[One-pager or checklist]
```

## Notes

- If the knowledge base has been built, search it first to find related content the agent has already published -- reference or link to it for internal consistency
- Never fabricate quotes or statistics not in the source material
- If the transcript quality is poor (auto-generated), flag sections that need the agent's review
