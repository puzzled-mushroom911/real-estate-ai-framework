# Using This Framework with the Claude Desktop App

This guide is for agents who want to use the Claude Desktop app instead of (or alongside) the Claude Code terminal. It covers what works, what doesn't, how to set it up, and where you'll hit limitations.

If you haven't done the initial setup yet, you still need to complete **Steps 1-6 from the main README** first. The Desktop app gives you a nicer visual interface, but the underlying tools still need to be installed on your machine.

---

## Understanding the Two Modes

The Claude Desktop app has two separate modes. This matters because they have different capabilities.

### Chat Mode (the default tab)

This is the regular Claude conversation you're used to from claude.ai. You type, Claude responds. You can attach files by dragging them in.

**What it CAN do:**
- Have conversations with Claude
- Attach images, PDFs, and documents
- Connect to cloud integrations (Gmail, Google Calendar, Supabase, Vercel)
- Use MCP tools that are configured in the Desktop app's own config file

**What it CANNOT do:**
- Read or write files on your computer
- Run terminal commands or scripts
- Use the framework's agents, skills, or rules
- Access your knowledge base databases directly
- Ingest YouTube channels
- Process CSV files
- Generate files (blog posts, emails, guides) and save them

**Bottom line:** Chat Mode is useful for quick questions, drafting text, and working with cloud integrations — but it can't interact with the framework's tools.

### Code Mode (the Code tab)

This is Claude Code running inside the Desktop app. It has a visual interface with file diffs, inline editing, and a sidebar — but under the hood, it's the same Claude Code from the terminal.

**What it CAN do:**
- Everything the terminal CLI can do
- Read and write files on your computer
- Run terminal commands and Python scripts
- Use all 5 agents, 2 skills, and content rules from this framework
- Query your knowledge base
- Ingest YouTube channels
- Generate and save blog posts, emails, guides
- Manage your CRM
- Use the persistent memory system
- Connect to all MCP servers

**What it CANNOT do:**
- Nothing significant — Code Mode has full capabilities

**Bottom line:** Code Mode is where the real work happens. If you're using the Desktop app, this is the tab you want.

---

## Setting Up the Desktop App

### 1. Download Claude Desktop

Download from [claude.ai/download](https://claude.ai/download) and install it. Log in with your Anthropic account.

### 2. Initial Framework Setup (One-Time)

You still need to do the initial setup from the main README. If you haven't done it yet, open Terminal (Finder > Applications > Utilities > Terminal) and run:

```bash
cd ~/
git clone <this-repo-url> "real-estate-ai"
cd "real-estate-ai"
bash scripts/setup.sh
```

This only needs to happen once. After this, you can use the Desktop app for everything.

### 3. Connect MCP Servers for Code Mode

MCP servers for Code Mode are configured in `~/.mcp.json` — the same file used by the terminal CLI. If you already set this up during the main README setup, you're done. If not:

Create or edit `~/.mcp.json`:

```json
{
  "mcpServers": {
    "real-estate-agent": {
      "command": "node",
      "args": ["/Users/YOURNAME/real-estate-ai/mcp_server/dist/index.js"]
    },
    "hostinger-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["hostinger-api-mcp@latest"],
      "env": {
        "API_TOKEN": "your-hostinger-api-token"
      }
    },
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=your-project-ref"
    }
  }
}
```

Replace `YOURNAME` with your macOS username and fill in your tokens.

### 4. Connect Cloud Integrations

These work in both Chat Mode and Code Mode:

1. Open Claude Desktop
2. Go to **Settings > Integrations**
3. Connect each service:
   - **Gmail** — lets Claude read, search, and draft emails
   - **Google Calendar** — lets Claude check your schedule and create events
   - **Vercel** — lets Claude deploy and manage websites
   - **Supabase** — lets Claude query and manage your database

Each one will ask you to authorize access to your account. Follow the prompts.

### 5. Open Your Framework in Code Mode

1. Open Claude Desktop
2. Click the **Code** tab
3. Use the folder picker to open `~/real-estate-ai`
4. Claude now has access to all your agents, skills, rules, knowledge bases, and tools

That's it — you're set up.

---

## Using Code Mode Day-to-Day

### Opening a Session

Every time you want to work:

1. Open Claude Desktop
2. Click **Code** tab
3. Open the `real-estate-ai` folder (or it may remember your last folder)
4. Start typing

### What You Can Ask

Everything from the main README works here. Some examples:

**Knowledge base queries:**
```
Search my knowledge base for what I've said about flood insurance
What have I covered about [neighborhood]?
```

**Content generation:**
```
Create a blog post from this transcript: [paste transcript]
Write a 5-email welcome sequence for new leads
Help me draft a response to this client inquiry: [paste message]
```

**CRM operations (if GoHighLevel is connected):**
```
Look up John Smith in my CRM
Show me all contacts tagged youtube-lead
Draft a text message to [contact]
```

**YouTube ingestion:**
```
Ingest my YouTube channel @MyHandle into the knowledge base
```
Claude will run the ingestion script for you — you don't need to open Terminal separately.

**Market analysis:**
```
Generate a CMA for 123 Main Street, Tampa FL
```

### Visual Advantages Over Terminal

The Desktop Code Mode gives you some things the terminal doesn't:

- **File diffs** — when Claude edits a file, you see a visual side-by-side diff with green/red highlighting
- **Inline approval** — you can approve or reject individual changes before they're applied
- **File tree** — see your project structure in the sidebar
- **Drag and drop** — drag images, PDFs, or documents directly into the conversation
- **Copy/paste images** — paste screenshots directly (Cmd+V)

---

## Using Chat Mode (Limited but Useful)

Chat Mode can't access the framework's tools directly, but it's still useful for certain tasks.

### What Chat Mode Is Good For

**Drafting content when you don't need the knowledge base:**
```
Write me a social media caption about [topic]
Draft a quick email response to this: [paste message]
Help me brainstorm content ideas for [topic]
```

**Working with cloud integrations:**
```
Check my Gmail for any messages from [name]
What's on my calendar this week?
Search my Supabase database for leads from Tampa
```

**Reviewing documents:**
Drag a PDF, screenshot, or document into the chat and ask Claude to review, summarize, or analyze it.

### What Chat Mode Cannot Do

- Search your local knowledge base (your ingested YouTube videos, documents, etc.)
- Run any of the framework's Python scripts
- Use the 5 agents (content repurposer, nurture writer, etc.)
- Save generated content to your computer
- Access your CRM through the framework's tools
- Process CSV files

For any of these tasks, switch to Code Mode.

---

## Dispatch: Sending Tasks From Your Phone

Dispatch is a feature for Pro and Max plan subscribers. It lets you message Claude from your phone and have it open a Code session on your Desktop app.

### How It Works

1. Open the Claude app on your phone
2. Go to the **Dispatch** tab
3. Type a task:
   ```
   Open a Code session in my real-estate-ai folder and
   generate a blog post from my latest YouTube video
   ```
4. Claude opens a Code session on your Desktop app and starts working
5. You can check progress on your phone or on your Desktop

### What Dispatch Is Good For

- Kicking off tasks while you're away from your computer
- "While I'm at this showing, generate a 5-email sequence about [topic]"
- "Pull up the conversation history for [client name] before my meeting"
- Starting long-running tasks (like ingesting a full YouTube channel) remotely

### Dispatch Limitations

- Your Desktop app must be open and running for Code sessions to start
- Approvals in Dispatch-spawned sessions expire after 30 minutes (in regular sessions, they last until the session ends)
- You can't drag-and-drop files from your phone — type everything as text
- Complex multi-step tasks may need you to check in on the Desktop to approve actions

---

## Limitations: Desktop vs. Terminal CLI

For most real estate agents, the Desktop app is the better choice. Here's the honest comparison:

### Desktop App Wins

| Feature | Desktop | Terminal |
|---|---|---|
| Visual file diffs | Color-coded side-by-side view | Text-only diffs |
| Approving changes | Click to approve/reject per change | Type yes/no |
| Drag and drop files | Drag images, PDFs directly in | Need to type file paths |
| Dispatch (phone tasks) | Available | Not available |
| Less intimidating | Feels like a chat app | Feels like hacking |

### Terminal CLI Wins

| Feature | Terminal | Desktop |
|---|---|---|
| Speed | Slightly faster for power users | Slight overhead from UI |
| Multiple sessions | Easy to run multiple terminals | One Code session at a time |
| Scripting | Can chain commands, pipe output | One command at a time |
| Background tasks | Run tasks in background easily | Tasks run in foreground |
| SSH / remote servers | Full access | Limited |

### No Difference

These work identically in both:
- All 5 agents, 2 skills, content rules
- Knowledge base queries
- MCP server connections
- YouTube ingestion
- Content generation (blogs, emails, guides)
- CRM operations
- CSV processing
- Memory system
- File reading and writing

---

## Recommended Setup for Real Estate Agents

If you're new to all of this, here's the simplest path:

1. **Use Terminal for the one-time setup** (Steps 1-6 from the main README)
2. **Use the Desktop app for everything after that** (Code Mode)
3. **Use Dispatch from your phone** when you want to kick off a task remotely
4. **Use Chat Mode** for quick drafts and cloud integrations (Gmail, Calendar)

You only need Terminal once. After that, the Desktop app does everything.

---

## Troubleshooting

**MCP tools aren't showing up in Code Mode:**
- Make sure `~/.mcp.json` exists and has the correct paths
- Restart the Desktop app after changing MCP config
- Check that the MCP server was built: `cd ~/real-estate-ai/mcp_server && npm run build`

**Knowledge base queries return nothing:**
- You need to ingest content first. In Code Mode, type: `Ingest my YouTube channel @MyHandle`
- Or run the script: tell Claude to `run bash scripts/ingest-channel.sh @MyHandle`

**Cloud integrations (Gmail, Calendar) aren't working:**
- Go to Settings > Integrations and re-authorize
- Some integrations require a Pro or Max plan

**Dispatch isn't available:**
- Dispatch requires a Pro or Max plan
- Your Desktop app must be open and logged in

**"Command not found" errors in Code Mode:**
- The terminal tools (Python, Node, yt-dlp) need to be installed first
- Run the setup steps from the main README in Terminal

---

## Quick Reference

| What you want to do | Where to do it |
|---|---|
| Search your knowledge base | Code Mode |
| Generate a blog post | Code Mode |
| Write nurture emails | Code Mode |
| Draft a client response | Code Mode |
| Draft a quick reply | Chat Mode or Code Mode |
| Check your Gmail | Chat Mode or Code Mode |
| Check your calendar | Chat Mode or Code Mode |
| Manage CRM contacts | Code Mode |
| Ingest YouTube channel | Code Mode |
| Process a CSV file | Code Mode |
| Deploy to Vercel | Chat Mode or Code Mode |
| Manage Hostinger hosting | Code Mode |
| Start a task from your phone | Dispatch |
