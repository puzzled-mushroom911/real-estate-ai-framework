# Installing as a Claude Code Plugin

This framework is a fully structured Claude Code plugin. You can install it from GitHub and get all the agents, skills, MCP tools, and content rules added to your Claude Code environment — whether you use the Terminal CLI, the Desktop app, or the web app.

---

## What You Get When You Install the Plugin

| Component | What it adds | Namespace |
|---|---|---|
| **5 Agents** | Content repurposer, nurture email writer, voice processor, CRM manager, customer response drafter | Visible in `/agents` |
| **2 Skills** | CMA generator (`/real-estate-agent:cma-generator`), customer response (`/real-estate-agent:customer-response`) | Invoked with `/real-estate-agent:` prefix |
| **MCP Server** | ~14 tools — knowledge base search, YouTube ingestion, content generation, CRM operations, CSV processing | Auto-connected |
| **Content Rules** | Fair Housing compliance, CON-to-PRO structure, no generic realtor language, voice matching | Applied automatically |
| **6 Strategy Books** | Hormozi + Brunson marketing frameworks, searchable via RAG | Queried automatically when generating content |
| **Email Templates** | Welcome sequences and nurture campaigns | Referenced by the nurture-writer agent |

---

## Installation Methods

### Method 1: Install from GitHub URL (Recommended)

This is the standard way to install a Claude Code plugin. Works in Terminal CLI, Desktop app (Code mode), or web app.

**Step 1: Install the plugin**

In any Claude Code session, type:

```
/plugin install https://github.com/puzzled-mushroom911/real-estate-ai-framework
```

Or use the CLI directly:

```bash
claude plugin install https://github.com/puzzled-mushroom911/real-estate-ai-framework
```

Claude Code downloads the plugin and registers its agents, skills, and MCP server configuration.

**Step 2: Install the Python tools and MCP server**

The plugin configuration tells Claude what tools exist, but the actual scripts need to be built on your machine. Navigate to the plugin directory and run the setup script:

```bash
cd ~/.claude/plugins/real-estate-agent
bash scripts/setup.sh
```

This installs Python packages (ChromaDB, LangChain, sentence-transformers), builds the MCP server, and downloads the embedding model (~80 MB, one time).

**Step 3: Personalize your profile**

Open Claude Code and say:

> "Help me set up my real estate agent profile"

Claude walks you through filling in your name, phone, brokerage, city, credibility line, and team description. This personalizes all content generation.

**Step 4: Verify the installation**

Run these to confirm everything is working:

```
/help
```
You should see `/real-estate-agent:cma-generator` and `/real-estate-agent:customer-response` listed.

```
/agents
```
You should see the 5 agents: content-repurposer, nurture-writer, voice-processor, crm-agent, customer-response.

Try a skill:
```
/real-estate-agent:customer-response Draft a reply to a buyer asking about flood insurance costs in my area
```

---

### Method 2: Clone and Use as Local Plugin (Development / Customization)

If you want to customize the plugin or contribute changes, clone the repo and load it as a local plugin.

**Step 1: Clone the repository**

```bash
cd ~/
git clone https://github.com/puzzled-mushroom911/real-estate-ai-framework.git real-estate-ai
cd real-estate-ai
```

**Step 2: Run setup**

```bash
bash scripts/setup.sh
```

**Step 3: Load as a local plugin**

```bash
claude --plugin-dir ~/real-estate-ai
```

This loads the plugin for that session. Your skills show up as `/real-estate-agent:cma-generator`, agents appear in `/agents`, and the MCP server connects.

**Step 4: Reload after changes**

If you edit any agent, skill, or hook files:

```
/reload-plugins
```

This picks up changes without restarting Claude Code.

---

### Method 3: Claude Desktop App (Code Mode)

The Desktop app provides a visual interface with file diffs, inline approval, and drag-and-drop.

**One-Time Setup (Terminal — 15 minutes)**

You need Terminal for the initial install only:

```bash
# Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# Close and reopen Terminal after Homebrew installs

# Install required tools
brew install python@3.12 node yt-dlp ffmpeg

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Clone and set up the framework
cd ~/ && git clone https://github.com/puzzled-mushroom911/real-estate-ai-framework.git real-estate-ai && cd real-estate-ai && bash scripts/setup.sh
```

**After That — Desktop Only**

1. Download Claude Desktop from [claude.ai/download](https://claude.ai/download)
2. Open it and click the **Code** tab
3. Open the `~/real-estate-ai` folder
4. Type: **"Help me set up"**

Claude handles the rest. You never need Terminal again.

---

## Plugin Structure (What's Inside)

This is what makes it a valid Claude Code plugin:

```
real-estate-ai-framework/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (name, version, description)
├── agents/                       # 5 specialized agents
│   ├── content-repurposer.md    # One piece of content → 5+ formats
│   ├── nurture-writer.md        # Lead nurture emails (Seinfeld framework)
│   ├── voice-processor.md       # Voice note → structured notes + action items
│   ├── crm-agent.md             # CRM contact and pipeline management
│   └── customer-response.md     # Style-matched client responses
├── skills/                       # 2 user-invokable + model-invokable skills
│   ├── cma-generator/
│   │   └── SKILL.md             # /real-estate-agent:cma-generator
│   └── customer-response/
│       └── SKILL.md             # /real-estate-agent:customer-response
├── .mcp.json                    # MCP server config (connects Python tools)
│
│   # Supporting infrastructure (not plugin-specific, but required):
├── mcp_server/                  # TypeScript MCP server (bridges Claude ↔ Python tools)
├── tools/                       # Python scripts (RAG, YouTube, content, CRM, CSV)
├── knowledge_bases/             # Books, prompts, vector stores, transcripts
├── config/                      # Agent profile, channel list, API keys
├── templates/                   # Email sequence templates
├── scripts/                     # Bash setup and ingestion scripts
├── my_data/                     # Your personal content sources
└── .claude/                     # Project-level config (CLAUDE.md, rules, memory)
```

The `.claude-plugin/plugin.json` manifest is what tells Claude Code "this is a plugin." The `agents/`, `skills/`, and `.mcp.json` at the root level are what the plugin system reads. Everything else supports the tools.

---

## How It Works for Your Team

### Sharing with Team Members

Each person on your team installs the plugin independently:

```
/plugin install https://github.com/puzzled-mushroom911/real-estate-ai-framework
```

Then runs setup and fills in their own profile. Each person gets:
- Their own personalized agents (writing in THEIR voice)
- Their own knowledge base (from THEIR content)
- Shared strategy books and email templates
- Same content rules and quality standards

### Co-Work Sessions

For real-time collaboration, use Claude Co-Work:

1. One person opens the framework in Code mode
2. Click **Share** or **Co-Work** to generate a session link
3. Team members join via the link

| Scenario | How it works |
|---|---|
| **Leader + assistant** | Leader has the knowledge base, assistant joins to generate content and manage CRM |
| **Multiple agents** | Each agent has their own profile — swap with "use [Name]'s profile" |
| **Agent + marketer** | Agent provides expertise (videos, voice notes), marketer uses Co-Work to create content packages |

### Dispatch (Phone → Desktop)

Pro/Max subscribers can send tasks from their phone:

1. Open Claude app on your phone → **Dispatch** tab
2. Type a task: "Generate a CMA for 123 Main St, Tampa FL"
3. Claude opens a Code session on your Desktop and starts working

Your Desktop app must be running for Dispatch to work.

---

## Updating the Plugin

When updates are published to the GitHub repo:

```
/plugin update real-estate-agent
```

Or if you cloned locally:

```bash
cd ~/real-estate-ai && git pull
```

Then run `/reload-plugins` in your Claude Code session to pick up changes.

---

## Troubleshooting

**Plugin not found after install:**
- Run `/help` and look for skills with the `real-estate-agent:` prefix
- Run `/reload-plugins` to force a reload
- Check that Claude Code is version 1.0.33 or later: `claude --version`

**MCP tools not connecting:**
- The MCP server needs to be built first: `cd <plugin-dir>/mcp_server && npm run build`
- Restart Claude Code after MCP config changes

**Skills not appearing:**
- Skills are namespaced: use `/real-estate-agent:cma-generator`, not `/cma-generator`
- Run `/reload-plugins` after any changes

**Setup script failed:**
- Python too old → `brew install python@3.12`
- npm permission error → `sudo npm install -g @anthropic-ai/claude-code`
- Network timeout → run `bash scripts/setup.sh` again

**Knowledge base returns nothing:**
You need to ingest content first. Say: "Ingest my YouTube channel @MyHandle"

---

## Quick Reference

| What you want to do | Command |
|---|---|
| Install the plugin | `/plugin install https://github.com/puzzled-mushroom911/real-estate-ai-framework` |
| Generate a CMA | `/real-estate-agent:cma-generator 123 Main St, Tampa FL` |
| Draft a client response | `/real-estate-agent:customer-response [paste message]` |
| See available agents | `/agents` |
| Reload after changes | `/reload-plugins` |
| Update the plugin | `/plugin update real-estate-agent` |
| Test locally | `claude --plugin-dir ./real-estate-ai` |
