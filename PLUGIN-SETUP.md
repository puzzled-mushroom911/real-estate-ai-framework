# Setting Up as a Claude Desktop Plugin or Co-Work Project

This guide is for real estate agents who want to use this framework through the **Claude Desktop app** or share it with their team via **Claude Co-Work** — no Terminal required after the initial install.

---

## Option 1: Claude Desktop App (Code Mode)

The Claude Desktop app gives you a visual, chat-like interface with all the same power as the Terminal version. This is the recommended setup for most agents.

### One-Time Setup (15 minutes)

You need Terminal for the initial install only. After this, you never need to open Terminal again.

**1. Open Terminal** (Finder > Applications > Utilities > Terminal)

**2. Install everything with these 4 commands** (copy-paste each one, press Enter):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
_(Close and reopen Terminal after this one finishes)_

```bash
brew install python@3.12 node yt-dlp ffmpeg
```

```bash
npm install -g @anthropic-ai/claude-code
```

```bash
cd ~/ && git clone https://github.com/puzzled-mushroom911/real-estate-ai-framework.git real-estate-ai && cd real-estate-ai && bash scripts/setup.sh
```

That last command downloads the framework AND runs the setup script. Wait for it to finish (2-5 minutes).

**3. Download the Claude Desktop App**

Go to [claude.ai/download](https://claude.ai/download), install it, and log in with your Anthropic account.

**4. Open the Framework in Code Mode**

1. Open Claude Desktop
2. Click the **Code** tab (not Chat)
3. Use the folder picker to open `~/real-estate-ai`
4. Type: **"Help me set up"**

Claude takes over from here. It asks for your name, phone, brokerage, etc. and configures everything.

**That's it. You're done with Terminal forever.**

---

## Option 2: Add as a Claude Code Plugin

Claude Code supports adding GitHub repositories as project plugins. This means you (or any agent on your team) can add this framework's capabilities to any Claude Code session.

### How It Works

When you add a GitHub repo as a plugin, Claude Code pulls in the project's configuration — the agents, skills, rules, knowledge base tools, and MCP server — and makes them available in your session. Think of it like installing an app on your phone.

### Setup

**Step 1: Add the GitHub Repo as a Plugin**

In Claude Code (Terminal or Desktop Code mode), run:

```bash
claude plugins add https://github.com/puzzled-mushroom911/real-estate-ai-framework.git
```

Or if you're in the Claude Desktop app, go to **Settings > Plugins** and paste the repo URL:

```
https://github.com/puzzled-mushroom911/real-estate-ai-framework.git
```

This pulls in all the agents, skills, rules, and configuration from the framework.

**Step 2: Run the Setup Script**

The plugin adds the configuration, but you still need the Python tools and MCP server installed locally. Open the plugin directory and run:

```bash
cd ~/real-estate-ai
bash scripts/setup.sh
```

**Step 3: Configure the MCP Server**

Add the framework's tool server to your `~/.mcp.json` so Claude can use the built-in tools (knowledge base search, YouTube ingestion, CRM, etc.):

```json
{
  "mcpServers": {
    "real-estate-agent": {
      "command": "node",
      "args": ["/Users/YOURNAME/real-estate-ai/mcp_server/dist/index.js"]
    }
  }
}
```

Replace `YOURNAME` with your macOS username.

**Step 4: Personalize**

Open Claude in the framework folder and say "help me set up." It walks you through filling in your profile.

### What the Plugin Gives You

Once installed, every Claude Code session in this folder has access to:

| Capability | What it means |
|---|---|
| **5 Agents** | Content repurposer, nurture email writer, voice note processor, CRM manager, customer response drafter |
| **2 Skills** | CMA generator, quick customer response |
| **~14 MCP Tools** | Knowledge base search, YouTube ingestion, content generation, CRM operations, CSV processing |
| **6 Strategy Books** | Hormozi + Brunson frameworks, searchable and auto-referenced |
| **Content Rules** | Fair Housing compliance, CON-to-PRO structure, no generic realtor language |
| **Email Templates** | Welcome sequences and nurture campaigns, pre-structured |

---

## Option 3: Claude Co-Work (Team Collaboration)

Co-Work lets multiple people collaborate in the same Claude session. This is useful for real estate teams where multiple agents or assistants need access to the same knowledge base and tools.

### How Co-Work Helps Real Estate Teams

| Scenario | How Co-Work handles it |
|---|---|
| **Team leader + assistant** | Leader sets up the framework once, assistant joins the session to generate content, draft responses, manage CRM |
| **Multiple agents on a team** | Each agent has their own profile but shares the team knowledge base — market data, neighborhood guides, review responses |
| **Agent + marketing person** | Agent provides the expertise (videos, voice notes), marketing person uses Co-Work to generate the content packages |
| **Training new agents** | New agent joins a session where the knowledge base already has market expertise, templates, and proven email sequences |

### Setting Up Co-Work

**1. Set up the framework** on the host machine (follow Option 1 or 2 above).

**2. Start a Co-Work session** in Claude Desktop:
- Open the framework folder in Code mode
- Click **Share** or **Co-Work** to generate a session link
- Send the link to your team member

**3. Team member joins** by clicking the link. They get access to the same agents, tools, knowledge base, and conversation context.

### Co-Work Limitations

- The framework and tools must be installed on the host machine
- Team members joining remotely can interact with Claude but can't run local scripts on THEIR machine — everything executes on the host
- Each person should still have their own agent profile for personalized content (swap profiles by telling Claude "use [Name]'s profile")

---

## Using Dispatch (Send Tasks From Your Phone)

If you have a Claude Pro or Max plan, Dispatch lets you send tasks to your Desktop app from your phone.

### Real Estate Use Cases

- **At a showing:** "Open my real-estate-ai folder and generate a CMA for 123 Oak Street, Tampa FL"
- **Driving between appointments:** "Write a follow-up email to the Johnsons about the house on Bayshore"
- **After recording a video:** "I just uploaded a new video to my channel — ingest it and start the post-production pipeline"
- **Before a meeting:** "Pull up everything I have on [client name] from my CRM and knowledge base"

### How to Use It

1. Open Claude app on your phone
2. Go to the **Dispatch** tab
3. Type your task and specify the `real-estate-ai` folder
4. Claude opens a Code session on your Desktop and starts working
5. Check progress on your phone or on your Desktop when you're back

Your Desktop app must be open and running for Dispatch to work.

---

## Quick Reference: Where to Do What

| Task | Best place to do it |
|---|---|
| Generate content (blogs, emails, social) | Desktop Code Mode |
| Search your knowledge base | Desktop Code Mode |
| Manage CRM contacts | Desktop Code Mode |
| Ingest YouTube channel | Desktop Code Mode |
| Process CSV files | Desktop Code Mode |
| Quick email draft (no knowledge base needed) | Desktop Chat Mode |
| Check Gmail | Desktop Chat Mode or Code Mode |
| Check Calendar | Desktop Chat Mode or Code Mode |
| Kick off a task remotely | Dispatch (phone) |
| Collaborate with team | Co-Work |

---

## Troubleshooting

**"I don't see the Code tab in Claude Desktop"**
Make sure you have Claude Desktop (not just claude.ai in a browser). Download from [claude.ai/download](https://claude.ai/download).

**"MCP tools aren't connecting"**
- Check that `~/.mcp.json` exists with the correct path to the MCP server
- Restart the Desktop app after changing MCP config
- In Code mode, ask Claude: "Check if the MCP server is connected"

**"Knowledge base returns nothing"**
You need to ingest content first. In Code mode: "Ingest my YouTube channel @YourHandle"

**"Setup script failed"**
Tell Claude what error you saw. Common fixes:
- Python too old → `brew install python@3.12`
- npm permission error → `sudo npm install -g @anthropic-ai/claude-code`
- Network timeout → run the setup script again

**"I want to update the framework"**
```bash
cd ~/real-estate-ai && git pull
```
Or in Claude Code mode: "Update the framework to the latest version"

---

## Summary

| Method | Best for | Setup time |
|---|---|---|
| **Desktop App (Code Mode)** | Solo agents who want a visual interface | 15 minutes |
| **Plugin from GitHub** | Agents who want to add capabilities to existing Claude setup | 10 minutes |
| **Co-Work** | Teams collaborating on content and CRM | 5 minutes (after host setup) |
| **Dispatch** | Agents who want to send tasks from their phone | Already included with Pro/Max |

Pick the one that fits how you work. They all use the same framework, same agents, same knowledge base.
