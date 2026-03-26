# Real Estate Agent AI Framework

## New User Onboarding
If this is a new user (placeholder values in `config/agent_profile.yaml`, no `config/.env`, etc.), read `llms.txt` in the project root and follow its guided setup flow. Walk the user through setup one step at a time -- don't dump all instructions at once. Detect what's already installed and skip completed steps.

## Overview
This is a Claude Code configuration framework for real estate agents who want an AI assistant that learns their voice and style from their own content and data. It ingests content from any source -- YouTube videos, podcasts, client reviews, website copy, sales conversations, voice notes -- and uses that to power content repurposing, lead nurture, CRM operations, and customer communication in the agent's authentic voice.

## Template Variables
Replace these placeholders with your actual information during setup:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{AGENT_NAME}}` | Your full name | Aaron Chand |
| `{{AGENT_PHONE}}` | Business phone number | (727) 472-7555 |
| `{{AGENT_EMAIL}}` | Business email | aaron@livinginstpetefl.com |
| `{{AGENT_WEBSITE}}` | Your website URL | https://livinginstpetefl.com |
| `{{AGENT_BROKERAGE}}` | Your brokerage name | Excellecore Real Estate |
| `{{AGENT_CITY}}` | Primary city you serve | St. Petersburg |
| `{{AGENT_STATE}}` | State | Florida |
| `{{AGENT_BOOKING_LINK}}` | Calendar booking URL | https://your-booking-link.com |
| `{{AGENT_CREDENTIAL_LINE}}` | Your credibility statement | "In the past couple years, we've helped over 50 buyers relocate to Tampa Bay." |
| `{{AGENT_TEAM_DESCRIPTION}}` | Team composition | "husband-wife team" / "solo agent" / "team of 3" |

## Directory Structure

```
.claude/
  CLAUDE.md              # This file -- project-level instructions
  rules/
    content-style.md     # Brand voice, hook formula, content positioning
    python-conventions.md # Python coding standards
    node-conventions.md   # Node/TypeScript coding standards
  agents/
    content-repurposer.md       # Multi-format content repurposing
    nurture-writer.md            # Lead nurture emails (Seinfeld framework)
    voice-processor.md           # Voice note transcript processing
    crm-agent.md                 # CRM contact and pipeline management
    customer-response.md         # Style-matched customer responses
  skills/
    cma-generator.md            # Comparative Market Analysis
    customer-response.md        # Quick response drafting
  memory/
    MEMORY.md                   # Auto-loaded memory index
```

## Tool & MCP Server Reference

### Knowledge Base Tools (RAG)
- `content_rag` -- Your content transcripts and copy (YouTube, podcasts, website, etc.), indexed for search
- `conversation_history` -- CRM conversation logs for style matching
- `neighborhood_data` -- Area-specific facts, schools, amenities, pricing
- `market_data` -- Current market conditions and trends

### CRM Tools (via MCP Server)
- Contact search, create, update, upsert
- Tag management (add/remove)
- Conversation search and message sending (SMS, email)
- Pipeline and opportunity management
- Task management

### Media Tools
- `yt-dlp` -- YouTube transcript and audio extraction
- `ffmpeg` -- Audio/video processing
- Standard file operations for content generation

## Scope Discipline
- When asked to do a simple task, do EXACTLY that -- do not over-engineer
- When asked for plain text output, deliver plain text FIRST
- Ask before expanding scope beyond what was explicitly requested
- Don't ask permission for search/read CRM calls -- just execute them
- DO ask permission before: creating contacts, sending messages, updating pipeline stages

## Sound Notifications
afplay /System/Library/Sounds/Frog.aiff

## Rules & Memory Architecture
- **Rules:** Content and coding conventions live in `.claude/rules/`
- **Memory:** Index at `memory/MEMORY.md` (auto-loaded). Topic files loaded on demand.
- **Agents:** Task-specific agents live in `.claude/agents/` -- invoke by task type
- **Skills:** Quick-action skills live in `.claude/skills/` -- invoke for rapid tasks

## Content Defaults
- Every piece of content must be Fair Housing compliant
- Use "buyers" not "families" -- avoid steering or demographic assumptions
- No generic realtor language -- ever
- CON-to-PRO structure: acknowledge negatives, then flip them
- Specific data over vague claims in all content
- All generated content should match the agent's voice as learned from their ingested content
