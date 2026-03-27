---
name: ingest
description: Ingest content into the agent's knowledge base. Use when asked to ingest YouTube videos, add documents, build a knowledge base, index content, or process transcripts for RAG search.
---

# Content Ingestion

Ingest content from any source into the agent's local knowledge base so it can be searched and referenced in all future work.

## Important Context

- The plugin root contains all scripts and tools. Find it by locating this SKILL.md file's parent directory and navigating up to the plugin root.
- Knowledge bases are stored locally on the agent's machine -- data never leaves their computer.
- The knowledge base powers voice matching, content generation, and accurate local information.

## Supported Sources

Ask the user what they'd like to ingest:

> "What content should I learn from? I can ingest:"
>
> 1. **YouTube channel** -- I'll download all your video transcripts
> 2. **Single YouTube video** -- paste the URL
> 3. **Documents** -- drag PDFs, Word docs, or text files into the chat
> 4. **Website pages** -- I'll scrape and index specific URLs
> 5. **CSV/spreadsheet data** -- client lists, market data, neighborhood info

## Process by Source Type

### YouTube Channel

```bash
bash <PLUGIN_ROOT>/scripts/ingest-channel.sh @ChannelHandle
```

While it runs, explain:

> "I'm downloading transcripts from your videos, splitting them into searchable chunks, and storing them in a local AI database. This is how I learn your voice and your expertise. It takes a few minutes depending on how many videos you have."

If the channel handle isn't configured yet, ask for it and update `<PLUGIN_ROOT>/config/channels.yaml`.

### Single YouTube Video

```bash
# Download transcript
yt-dlp --write-auto-sub --sub-lang en --skip-download -o "<PLUGIN_ROOT>/knowledge_bases/transcripts/%(title)s" "<URL>"

# Ingest into knowledge base
python3 <PLUGIN_ROOT>/tools/rag_tools/create_knowledge_base.py \
  "<PLUGIN_ROOT>/knowledge_bases/transcripts/" \
  --db-dir "<PLUGIN_ROOT>/knowledge_bases/vectors/youtube_single"
```

### Documents (PDF, DOCX, TXT)

Ask the user to drag files into the chat or provide file paths, then:

```bash
python3 <PLUGIN_ROOT>/tools/rag_tools/create_knowledge_base.py \
  "<file_path>" \
  --db-dir "<PLUGIN_ROOT>/knowledge_bases/vectors/local_documents"
```

For multiple files, process them all into the same database:

```bash
python3 <PLUGIN_ROOT>/tools/rag_tools/create_knowledge_base.py \
  "<file1>" "<file2>" "<file3>" \
  --db-dir "<PLUGIN_ROOT>/knowledge_bases/vectors/local_documents"
```

### Website Pages

```bash
bash <PLUGIN_ROOT>/scripts/scrape-web.sh "<URL>" "<PLUGIN_ROOT>/knowledge_bases/vectors/web_content"
```

### CSV/Spreadsheet Data

```bash
bash <PLUGIN_ROOT>/scripts/process-csv.sh "<file_path>" "<PLUGIN_ROOT>/knowledge_bases/vectors/structured_data"
```

## After Ingestion

Confirm what was ingested and what it enables:

> "Done! I've indexed [X items/videos/pages] into your knowledge base. Here's what this unlocks:"
>
> - **Content repurposing** -- I can now turn any of your videos into blog posts, emails, and social media in your voice
> - **Customer responses** -- I'll match your communication style when drafting replies
> - **Lead nurture emails** -- your email sequences will sound like you, not a template
> - **CMA context** -- I can reference your past market commentary for consistency

Offer to do something with the newly ingested content:

> "Want me to do something with this right now? I could:"
>
> 1. Repurpose your most recent video into a blog post and emails
> 2. Draft a welcome email sequence in your voice
> 3. Search your knowledge base for a specific topic

## Error Handling

- If `yt-dlp` is not installed: "I need yt-dlp to download YouTube transcripts. Run the setup skill first, or I can install it now with `brew install yt-dlp`."
- If Python dependencies are missing: "The knowledge base tools need some Python packages. Run the setup skill, or I can install them now."
- If a YouTube URL is invalid: "That doesn't look like a valid YouTube URL. Can you double-check it?"
- If a file can't be read: "I couldn't read that file. Make sure it's a PDF, Word doc, or text file and try dragging it in again."
- For ANY error: explain in plain language what went wrong and offer a fix. Never show raw error output alone.
