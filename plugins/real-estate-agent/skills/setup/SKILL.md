---
name: setup
description: First-time setup wizard for the Real Estate Agent plugin. Installs all dependencies, builds the MCP server, configures the agent profile, and optionally ingests YouTube content. Run this once after installing the plugin. Use when the user says "set up", "get started", "configure", or "help me set up".
---

# Real Estate Agent Plugin — First-Time Setup

You are guiding a real estate agent through first-time setup of this plugin. They are using Claude Desktop and are NOT technical. Walk them through ONE step at a time. Do NOT dump all instructions at once. Confirm each step worked before moving to the next.

## Important Context

- The plugin files are installed at a cache location. Find the plugin root by locating this SKILL.md file's parent directory and navigating up to the plugin root (the directory containing `.claude-plugin/plugin.json`).
- Store the plugin root path in a variable for all subsequent commands.
- All commands run inside Claude Desktop Code mode — the user never needs to open Terminal.

## Phase 1: Check Prerequisites

Run these checks silently (don't ask permission):

```bash
command -v brew && echo "BREW: installed" || echo "BREW: missing"
command -v python3 && python3 --version || echo "PYTHON: missing"
command -v node && node --version || echo "NODE: missing"
command -v yt-dlp && echo "YT-DLP: installed" || echo "YT-DLP: missing"
command -v ffmpeg && echo "FFMPEG: installed" || echo "FFMPEG: missing"
```

Based on results, tell the user ONLY what's missing. Example:

> "You already have Python and Node installed. You just need yt-dlp and ffmpeg. I'll install those for you now."

If Homebrew is missing, explain:

> "I need to install Homebrew first — it's like an app store that lets me install the tools this plugin needs. It will ask for your Mac password. You won't see characters as you type — that's normal."

Then give them the command to paste (Homebrew requires interactive password input):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After Homebrew, install missing tools:

```bash
brew install python@3.12 node yt-dlp ffmpeg
```

Tell the user what each tool does in one sentence:
- **Python**: Runs the scripts that process your content into a searchable knowledge base
- **Node.js**: Runs the server that connects me to your real estate tools
- **yt-dlp**: Downloads YouTube transcripts so I can learn from your videos
- **ffmpeg**: Processes audio and video files

## Phase 2: Install Python Dependencies

Find the plugin root directory, then install Python packages:

```bash
pip3 install chromadb sentence-transformers langchain langchain-community langchain-text-splitters python-dotenv requests PyPDF2 docx2txt
```

Tell the user:

> "Installing the AI packages that power your knowledge base. This downloads about 80 MB of AI models — it's a one-time thing."

## Phase 3: Build the MCP Server

Navigate to the plugin's mcp_server directory and build:

```bash
cd <PLUGIN_ROOT>/mcp_server && npm install && npm run build
```

Tell the user:

> "Building the tool server that lets me search your knowledge base, process content, and manage your CRM. This takes about a minute."

After this completes, tell them:

> "The tools are built. You'll need to restart Claude Desktop once for the tools to connect. But let's finish the rest of the setup first."

## Phase 4: Agent Profile

This is the most important step. Tell the user:

> "Now I need your information so everything I create — emails, blog posts, client responses — uses your name, your branding, and your credibility. Let me ask you a few questions."

Ask these ONE at a time (not all at once):

1. What's your full name?
2. What's your business phone number?
3. What's your business email?
4. What's your website URL?
5. What brokerage are you with?
6. What city and state do you primarily serve?
7. Do you have a YouTube channel? If so, what's the handle? (optional)
8. Do you have a calendar/booking link for clients? (optional)
9. What's your credibility line? Example: "Over 8 years helping buyers relocate to Tampa Bay." — make it specific and provable.
10. How would you describe your team? (solo agent, husband-wife team, team of 3, etc.)

After collecting answers, write them to `<PLUGIN_ROOT>/config/agent_profile.yaml` using this format:

```yaml
agent:
  name: "[Their answer]"
  phone: "[Their answer]"
  email: "[Their answer]"
  website: "[Their answer]"
  brokerage: "[Their answer]"
  city: "[Their answer]"
  state: "[Their answer]"
  booking_link: "[Their answer or empty]"
  credential_line: "[Their answer]"
  team_description: "[Their answer]"

content_sources:
  youtube:
    - handle: "[Their channel handle or empty]"
      name: "[Their channel name or empty]"
      db_name: "youtube_my_channel"

paths:
  knowledge_bases: "<PLUGIN_ROOT>/knowledge_bases/vectors"
  transcripts: "<PLUGIN_ROOT>/knowledge_bases/transcripts"
```

Confirm: "Your profile is set up. Everything I generate will use your name, your branding, and your credibility line."

## Phase 5: Content Ingestion (Optional but Recommended)

Ask:

> "Now let's give me something to learn from so that everything I write sounds like you. Which of these do you have?"
>
> 1. **YouTube channel** — I'll download your video transcripts and make them searchable
> 2. **Documents** (market reports, guides, PDFs) — I'll index them for reference
> 3. **Neither right now** — that's fine, we can do this later

### If YouTube:

```bash
bash <PLUGIN_ROOT>/scripts/ingest-channel.sh @TheirHandle
```

While it runs, explain:

> "I'm downloading transcripts from your recent videos, splitting them into searchable chunks, and storing them in a local database on your computer. This data never leaves your machine."

### If Documents:

Tell them to drag files into the chat or provide paths, then:

```bash
python3 <PLUGIN_ROOT>/tools/rag_tools/create_knowledge_base.py <document_path> --db-dir <PLUGIN_ROOT>/knowledge_bases/vectors/local_documents
```

### If Neither:

> "No problem. The agents and skills work great on their own. You can ingest content anytime by saying 'ingest my YouTube channel' or dragging documents into the chat."

## Phase 6: First Real Task

Don't end on setup. Give them a win:

> "Setup is done! Want me to do something real right now? Pick one:"
>
> 1. Write a 5-email welcome sequence for new leads
> 2. Draft a response to a buyer question (paste one in)
> 3. Generate a CMA for a property address
> 4. Search your knowledge base for a topic (if you ingested content)

Whatever they pick, do it. This proves everything works and gives them immediate value.

## Phase 7: Remind to Restart

At the very end, remind them:

> "One last thing — restart Claude Desktop so the MCP tools connect. After that, everything is ready to go. You can use any of the skills and agents anytime."

## Error Handling

- If `brew install` fails: check internet connection, retry
- If `pip3 install` fails: try `python3 -m pip install` instead
- If `npm install` fails: check Node version (`node --version` should be 18+), try `brew install node`
- If YouTube ingestion fails: check the channel handle is correct, ensure yt-dlp is installed
- For ANY error: explain what happened in plain language and suggest a fix. Never show raw error output without context.
