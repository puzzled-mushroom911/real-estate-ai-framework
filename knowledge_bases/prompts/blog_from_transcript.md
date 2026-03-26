# Blog Post from Transcript Prompt

## Purpose
Transform a YouTube video transcript into an SEO-optimized blog post that captures the speaker's voice and expertise.

## Input
- Raw or cleaned transcript text
- Video title and YouTube ID
- Agent name and website

## Process

### 1. Voice Analysis
Read the transcript and identify:
- Speaking style (formal, conversational, authoritative, friendly)
- Recurring phrases or verbal patterns
- How they structure arguments (data-first, story-first, problem-solution)
- Level of technical detail they use

### 2. Content Extraction
From the transcript, extract:
- Main thesis / primary argument
- 3-5 key subtopics discussed
- Any data points, statistics, or specific claims
- Stories or anecdotes told
- Questions addressed or raised
- Calls to action mentioned

### 3. Research Enhancement
Web search for 3-5 supporting sources:
- Current market data that supports claims in the video
- Authoritative sources (NAR, Census, local MLS stats)
- Related topics for internal/external linking

### 4. SEO Structure
- **Title**: 50-60 characters, primary keyword near front
- **Meta Description**: 150-160 characters with CTA
- **H1**: Match or closely mirror title
- **H2s**: Each major section, keyword-rich
- **H3s**: Subsections where needed
- **Primary keyword**: In first 100 words, 1-2% density
- **LSI keywords**: 5+ semantically related terms woven naturally
- **FAQ section**: 5 questions derived from search intent
- **External links**: 3-5 authoritative sources
- **Internal links**: To related pages on agent's site

### 5. Writing Guidelines
- 1,500-2,500 words
- Maintain the speaker's voice (don't over-formalize)
- CON-to-PRO structure where the video uses it
- Include specific names, prices, streets (not generic language)
- Embed the YouTube video near the top
- Add timestamp links to key sections in the video
- End with a clear CTA matching the video's CTA

## Output Format
Markdown with YAML frontmatter:
```yaml
---
title: ""
date: "YYYY-MM-DD"
author: "{{AGENT_NAME}}"
excerpt: ""
tags: []
youtubeId: ""
metaDescription: ""
keywords: ""
---
```
