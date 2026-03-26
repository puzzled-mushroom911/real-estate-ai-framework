# Claude Code for Real Estate Agents

**What this is:** An AI assistant that learns YOUR voice and content, wherever it lives. Feed it your YouTube videos, podcast episodes, reviews, website, and client conversations — and it writes content, emails, and responses that sound like you. Not generic AI output. You.

**Who built it:** A real estate team ([Living in St. Pete](https://www.youtube.com/@livinginst-pete)) that uses this exact system to power their content, lead nurture, and client communication — packaged so any agent can use it.

**What you need:** A Mac, about 20 minutes, and a Claude subscription.

---

# Part 1: Getting Set Up

Claude Code can actually walk you through this setup interactively. Once you get to Step 5, just open Claude Code in this folder and say "help me set up" — it knows what to do.

But if you prefer to follow written instructions, here's every step.

---

## Step 1: Open Terminal

**What it is:** Terminal is a text-based way to talk to your computer. Instead of clicking buttons, you type commands. It sounds old-school, but it's how every powerful tool on your Mac works under the hood.

**How to open it:** Finder > Applications > Utilities > Terminal

**What you need to know:** You'll copy commands from this guide and paste them into Terminal. That's it. You don't need to memorize anything or learn to code.

---

## Step 2: Install Homebrew

**Why:** Your Mac doesn't come with everything this framework needs. Homebrew is like an app store for Terminal — it lets you install tools with one command instead of hunting for download links.

**What to do:** Paste this into Terminal and press Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It will ask for your Mac password (the same one you use to log in). Type it — you won't see characters appear, that's normal. Follow any prompts it gives you.

**When it's done:** Close Terminal completely and reopen it. This is important — it won't work properly until you do.

> Already have Homebrew? Skip this step.

---

## Step 3: Install the Tools This Framework Needs

**Why:** This framework uses four tools to do its work. Each one has a specific job:

| Tool | What it does | Why you need it |
|---|---|---|
| **Python** | Runs the scripts that process your data | Powers the knowledge base, content generation, and data cleanup |
| **Node.js** | Runs the server that connects Claude to your tools | Without this, Claude can't use the ~14 built-in tools |
| **yt-dlp** | Downloads YouTube transcripts | This is how your videos become searchable — no YouTube API key needed, completely free |
| **ffmpeg** | Processes audio and video files | Needed for extracting audio from videos or processing voice notes and podcast episodes |

**What to do:** Paste this one line into Terminal:

```bash
brew install python@3.12 node yt-dlp ffmpeg
```

This takes a minute or two. When it's done, you'll see your Terminal prompt again.

---

## Step 4: Install Claude Code

**Why:** Claude Code is the AI that runs everything in this framework. It's different from the regular Claude chat — it can read files, run scripts, manage your CRM, and interact with all the tools we're about to set up. Think of it as Claude with its hands untied.

**What to do:**

```bash
npm install -g @anthropic-ai/claude-code
```

Then start it for the first time:

```bash
claude
```

It will ask you to log in. Follow the prompts to authenticate with your Anthropic account.

> Already have Claude Code? Update it: `npm update -g @anthropic-ai/claude-code`

---

## Step 5: Download This Framework

**Why:** This is the actual toolkit — the agents, scripts, knowledge bases, templates, and configuration that turn Claude Code into a real estate machine.

**What to do:**

```bash
cd ~/
git clone https://github.com/YOUR-ORG/real-estate-ai-framework.git "real-estate-ai"
cd "real-estate-ai"
```

You now have a folder called `real-estate-ai` in your home directory with everything in it.

---

## Step 6: Run the Setup Script

**Why:** This script installs all the behind-the-scenes pieces — the Python libraries that power the knowledge base, the AI model that processes your content, and the server that connects Claude to your tools. It's one command instead of doing 20 things manually.

**What to do:**

```bash
bash scripts/setup.sh
```

**What's happening:** You'll see progress updates as it:
1. Installs Python packages (knowledge base engine, text processing, document handling)
2. Builds the MCP server (the bridge between Claude and your tools)
3. Downloads the AI embedding model (~80 MB, one time only — this is the model that makes your content searchable)
4. Creates your local config directory

Takes 2-5 minutes depending on your internet speed.

---

## Step 7: Tell Claude Who You Are

**Why:** Everything Claude generates — emails, blog posts, CRM operations, client responses — uses your name, your phone number, your credibility line, and your brand voice. This profile is the foundation for all of it.

**What to do:** Open `config/agent_profile.yaml` in any text editor. Replace the placeholders with your real information:

```yaml
agent:
  name: "Jane Smith"
  phone: "(555) 123-4567"
  email: "jane@janesmithrealty.com"
  website: "https://www.janesmithrealty.com"
  brokerage: "Sunshine Realty"
  city: "Tampa"
  state: "FL"
  booking_link: "https://calendly.com/jane-smith"
  credential_line: "Over 8 years helping buyers relocate to Tampa Bay."
  team_description: "solo agent"
```

The **credential line** is important — this shows up in email signatures and content hooks. Make it specific and provable. "Over 8 years helping buyers relocate to Tampa Bay" is good. "The best agent in Tampa" is not.

The **team description** tells Claude whether to write as "I" (solo agent) or "we" (team).

> See `examples/sample_agent_profile.yaml` for a complete filled-out example.

---

## Step 8: API Keys (Most Are Optional)

**Why:** Some features connect to external services like your CRM. But the core features — knowledge base, content generation, emails, client responses — work without any API keys at all.

**What to do:**

```bash
cp config/.env.example config/.env
```

Then open `config/.env` and add any keys you have:

| Key | What it unlocks | Where to get it | Do you need it? |
|---|---|---|---|
| `CRM_API_KEY` | Manage contacts, send messages, view pipeline | GoHighLevel > Settings > API Keys | Only if you use GoHighLevel |
| `CRM_LOCATION_ID` | Identifies your CRM location | GoHighLevel > Settings | Only if you use GoHighLevel |
| `ANTHROPIC_API_KEY` | AI-enhanced content generation | console.anthropic.com > API Keys | Nice to have, not required |

**Don't have any keys?** Skip this step entirely. Come back when you want to add integrations.

---

## Step 9: Connect Claude to Your Tools (MCP Servers)

**Why:** MCP stands for Model Context Protocol. It's how Claude Code gains superpowers beyond just chatting — it's the difference between an AI that can only talk and an AI that can actually do things. Each MCP server gives Claude access to a different service.

### The Framework Tools (Required)

**Why:** This connects Claude to the ~14 tools built into this framework — knowledge base search, content processing, CRM operations, and more. Without this, Claude can chat but can't use any of the real estate tools.

Run this to see your config entry:
```bash
echo '    "real-estate-agent": {
      "command": "node",
      "args": ["'$(pwd)'/mcp_server/dist/index.js"]
    }'
```

Add the output to your `~/.mcp.json` file. (See the complete example at the end of this section.)

### Hostinger (Website Management) — Optional

**Why:** If you host your website through Hostinger, this lets Claude manage your hosting, update DNS records, and deploy website changes without you logging into the Hostinger dashboard.

1. Log into [Hostinger](https://www.hostinger.com) > Account > API Tokens
2. Create a new token
3. Add to `~/.mcp.json`:

```json
"hostinger-mcp": {
  "type": "stdio",
  "command": "npx",
  "args": ["hostinger-api-mcp@latest"],
  "env": {
    "API_TOKEN": "your-hostinger-api-token"
  }
}
```

### Supabase (Cloud Database) — Optional

**Why:** Supabase gives you a cloud database for things like storing lead data, tracking analytics, or building web apps. It has a free tier and Claude can create tables, run queries, and manage your data directly.

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project — your **project ref** is in the URL: `supabase.com/project/YOUR_REF`
3. Add to `~/.mcp.json`:

```json
"supabase": {
  "type": "http",
  "url": "https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_REF"
}
```

### Claude in Chrome (Browser Control) — Optional

**Why:** This lets Claude see and interact with web pages in your browser. It can read a competitor's website, scrape your Google reviews, fill out forms, or take screenshots. It's like giving Claude eyes on the internet.

1. Open Chrome > [Chrome Web Store](https://chromewebstore.google.com)
2. Search for **"Claude in Chrome"** and install it
3. Click the extension icon and follow setup prompts
4. No `.mcp.json` entry needed — it connects automatically

### Gmail — Optional

**Why:** Lets Claude read, search, and draft emails directly in your Gmail. Useful for finding past client conversations or drafting follow-ups without switching tabs.

1. In Claude Code: Settings > Integrations (or visit claude.ai/settings)
2. Find **Gmail** > Click **Connect** > Authorize your Google account

### Google Calendar — Optional

**Why:** Lets Claude check your availability, create showing appointments, and manage your schedule. Useful when a lead asks "when are you free?" and Claude can actually check.

1. In Claude Code: Settings > Integrations (or visit claude.ai/settings)
2. Find **Google Calendar** > Click **Connect** > Authorize your Google account

### Vercel (Website Deployments) — Optional

**Why:** If your website runs on Vercel (a popular hosting platform for modern websites), Claude can deploy updates, check build status, and manage your web projects.

1. In Claude Code: Settings > Integrations (or visit claude.ai/settings)
2. Find **Vercel** > Click **Connect** > Authorize your account

### Your Complete .mcp.json File

Here's what the finished file looks like with all local MCP servers. Only include the ones you're using:

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

Replace `YOURNAME` with your macOS username. Replace tokens and project refs with your own.

---

## Step 10: Feed Claude Your Content

**Why:** This is where the magic happens. Claude is smart, but it doesn't know YOUR market, YOUR opinions, YOUR expertise, or how YOU talk to clients. This step teaches it. The more content you feed it, the more it sounds like you — not like a generic AI.

### Your Content Sources

Claude can learn from anything you give it. Here's what you can feed it and how:

| Content Source | What Claude learns from it |
|---|---|
| **YouTube channel** | Your opinions, expertise, market takes, and how you explain things on camera |
| **Podcast episodes** | Your speaking style, interview answers, and deep-dive topics |
| **Google / Zillow reviews** | What clients say about you — Claude uses this for social proof and understanding your strengths |
| **Website content** | Your bio, listings, blog posts, neighborhood pages, and brand messaging |
| **Sales history CSV** | Your track record — areas, price points, transaction volume |
| **Leads database CSV** | Lead sources, stages, follow-up patterns |
| **Voice recordings / voice notes** | How you actually talk — Claude matches your tone, phrasing, and cadence |

### YouTube Channel

If you have a YouTube channel, this is the fastest way to give Claude a deep understanding of your voice and expertise.

```bash
bash scripts/ingest-channel.sh @YourChannelHandle
```

**What's happening:** This downloads transcripts from your recent videos, splits them into searchable chunks, and stores them in a local database on your computer. Nothing is uploaded anywhere.

After this, you can ask Claude things like:
- "What have I said about flood insurance?"
- "Find everywhere I've talked about [neighborhood]"
- "What's my take on the current market?"

And it will pull from YOUR actual words.

### Website and Reviews

```bash
bash scripts/scrape-web.sh https://www.yourwebsite.com
```

Claude reads your website pages, Google reviews, or Zillow profile and makes them searchable. This is how it learns your brand messaging and what clients say about you.

### Data Files (Sales, Leads, Conversations)

```bash
python3 tools/data_importers/process-csv.sh your-data-file.csv
```

Export your sales history, leads database, or CRM conversations as a CSV. Claude cleans the data, structures it, and adds it to your knowledge base. This is especially powerful for:
- Understanding your price points and areas of expertise
- Matching how you respond to different types of client questions
- Identifying patterns in your lead sources and conversion

### Documents (PDFs, Market Reports, Guides)

Drop files into `knowledge_bases/documents/` and run:
```bash
python3 tools/rag_tools/create_knowledge_base.py knowledge_bases/documents/ --db-dir knowledge_bases/vectors/local_documents
```

Any PDFs, market reports, or guides you've written become searchable.

### Voice Notes and Podcast Episodes

Drop audio files into a folder and Claude will transcribe and process them using ffmpeg. Just tell Claude:

- **"Transcribe these voice notes and add them to my knowledge base"**
- **"Process this podcast episode and make it searchable"**

### Competitor Channels (Optional)

If you want Claude to know what competitors in your market are saying, you can ingest their public YouTube content too:

```bash
bash scripts/ingest-channel.sh @CompetitorHandle
```

This is optional — the framework is designed to work entirely from your own content.

---

## Step 11: Try It

```bash
cd ~/real-estate-ai
claude
```

Start with these to see it working:

| What to try | What happens |
|---|---|
| "Search my knowledge base for [topic from your content]" | Claude finds your exact quotes and opinions on that topic |
| "Create a blog post from my latest YouTube video" | A 1,500-2,500 word SEO blog post in your voice |
| "Write a 5-email welcome sequence for new leads" | Story-driven nurture emails using the Daily Seinfeld framework |
| "Draft a response to this buyer: [paste their message]" | A reply that matches how you actually communicate |
| "Generate a CMA for [address]" | A comparative market analysis summary |
| "Turn this transcript into a blog post, 3 emails, and social clips" | Full content repurposing from a single piece of content |

**You're set up.** Everything below is for when you're ready to go deeper.

---

# Part 2: What You Can Do With This

Part 1 got Claude connected. Part 2 is about putting it to work.

---

## Turn One Piece of Content Into Five Formats

This is the core workflow. You create one piece of content — a video, a podcast episode, a voice note — and Claude turns it into a full content package:

```
Tell Claude: "Run the post-production pipeline on this transcript"
```

What you get back:
- **SEO blog post** (1,500-2,500 words) ready for your website
- **3 nurture emails** — story-driven, 200 words each, using Russell Brunson's Daily Seinfeld method
- **3-5 social media clip scripts** with exact timestamps for cutting
- **Metadata** — optimized title, full description, tags, and thumbnail text suggestions

Works with YouTube transcripts, podcast transcripts, or any long-form content you've created.

## Write Emails That Sound Like You

Claude writes nurture emails using proven frameworks from the marketing books included in this repo:

```
"Write a 5-email welcome sequence for new leads"
"Create a nurture email about why insurance costs aren't as bad as people think"
```

Every email follows Story-Hook-Value-Invite structure. Max 200 words. Plain text. One CTA. No generic realtor language. Claude pulls from your actual content to match your voice and opinions.

## Manage Your CRM Without Opening a Browser

If you connected GoHighLevel:

```
"Look up John Smith in my CRM"
"Send a text to [contact] saying [message]"
"Show me all contacts tagged youtube-lead"
"Move [contact] to the Showing Properties stage"
```

## Import and Clean Your Data

Claude can process CSV files — clean contact lists, standardize phone numbers, flag duplicates, and import data into your knowledge base:

```
"Clean this contact list CSV and standardize the phone numbers"
"Import this CSV of past conversations into my knowledge base"
"Analyze my sales history and tell me my average price point by area"
"Find duplicate contacts in this lead list"
```

## Draft Client Responses

Paste a message from a buyer, seller, or lead, and Claude writes a response that matches how you actually communicate:

```
"Draft a response to this buyer: [paste their message]"
"This lead asked about flood zones — write a reply using what I've said in my videos"
"Respond to this Zillow inquiry in my voice"
```

Claude searches your knowledge base for relevant content you've created, then drafts a response using your words, your data points, and your communication style.

---

## What's Included

### 5 Agents

These are specialized assistants for specific jobs. You don't need to configure them — just describe what you need.

| Agent | What it handles |
|---|---|
| **content-repurposer** | One piece of content (video, podcast, voice note) into multiple formats |
| **nurture-writer** | Lead nurture emails using the Daily Seinfeld framework |
| **voice-processor** | iPhone voice notes into structured notes and action items |
| **crm-agent** | Contact management, messaging, pipeline updates |
| **customer-response** | Client replies that match your voice and communication style |

### 6 Marketing & Strategy Books

Pre-loaded and searchable in `knowledge_bases/books/`. Claude references these when generating content, offers, emails, funnels, and strategy:

| Book/Framework | Author |
|---|---|
| $100M Offers | Alex Hormozi |
| $100M Leads | Alex Hormozi |
| Pricing Playbook | Alex Hormozi |
| Ad Copywriting Framework | Alex Hormozi |
| DotCom Secrets | Russell Brunson |
| Traffic Secrets | Russell Brunson |

### 2 Skills

Quick commands for common tasks:

| Skill | What it does |
|---|---|
| **cma-generator** | Generates a comparative market analysis summary for any address |
| **customer-response** | Drafts a client response matched to your voice |

### ~14 MCP Tools

Knowledge base search, content processing, CRM operations, CSV cleanup, and data import — all callable by Claude behind the scenes.

---

## FAQ

**What if I don't have a YouTube channel?**
No problem — YouTube is just one content source. Feed Claude your podcast episodes, website content, reviews, voice notes, sales data, or any combination. The framework learns your voice from whatever you give it. YouTube is not required.

**Do I need to pay for anything beyond Claude Code?**
No. The framework is free. All the content processing runs on your computer.

**Can I use a CRM other than GoHighLevel?**
The CRM tools are built for GHL. If you use something else, skip the CRM integration — the content and communication tools are where most of the value is.

**Is my data private?**
Yes. Everything stays on your computer. No content is uploaded anywhere. The only external connections are to YouTube (downloading public transcripts), your CRM (if connected), and cloud services you choose to connect.

**Can I share this with my team?**
Yes. Each person clones the repo, runs setup, and fills in their own profile.

---

## Credits

Built by [Aaron Chand](https://www.youtube.com/@livinginst-pete) using:
- **Russell Brunson** — Epiphany Bridge and Daily Seinfeld email frameworks
- **Alex Hormozi** — Lead magnet, offer, and ad frameworks
- **LangChain + ChromaDB** — Local AI search infrastructure
- **Model Context Protocol (MCP)** — Claude Code tool integration

Also see: **[DESKTOP-SETUP.md](DESKTOP-SETUP.md)** — guide for using this with the Claude Desktop app instead of Terminal.

---

## License

MIT License. Use it, modify it, share it.
