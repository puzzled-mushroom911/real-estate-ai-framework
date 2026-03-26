/**
 * YouTube processing tools.
 * Wraps Python scripts for fetching transcripts, ingesting to RAG,
 * analyzing channel content, and querying YouTube strategy knowledge.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { executePython } from "../utils/python.js";
import { getConfig, getToolsDir } from "../utils/config.js";

export function registerYoutubeTools(server: McpServer): void {
  const config = getConfig();

  // ── youtube_fetch_videos ─────────────────────────────────────────────────
  server.tool(
    "youtube_fetch_videos",
    "Download transcripts and metadata from a YouTube channel. Uses yt-dlp to fetch video data including auto-generated captions.",
    {
      channel: z
        .string()
        .describe("YouTube channel URL, handle (@name), or channel ID"),
      days: z
        .number()
        .int()
        .min(1)
        .optional()
        .describe("Only fetch videos published in the last N days"),
      max: z
        .number()
        .int()
        .min(1)
        .max(500)
        .optional()
        .describe("Maximum number of videos to fetch (default: 50)"),
    },
    async ({ channel, days, max }) => {
      const args = ["--channel", channel];
      if (days !== undefined) args.push("--days", String(days));
      if (max !== undefined) args.push("--max", String(max));

      const result = await executePython(
        getToolsDir("youtube_tools", "fetch_videos.py"),
        args,
        { pythonPath: config.python_path, timeout: 300_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error fetching videos from "${channel}":\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── youtube_ingest ───────────────────────────────────────────────────────
  server.tool(
    "youtube_ingest",
    "Ingest downloaded YouTube transcripts into a RAG knowledge base for later querying. Processes transcript files, chunks them, and stores embeddings.",
    {
      transcript_dir: z
        .string()
        .describe("Path to directory containing transcript files to ingest"),
      db_name: z
        .string()
        .describe("Name of the RAG database to ingest transcripts into"),
    },
    async ({ transcript_dir, db_name }) => {
      const args = ["--input", transcript_dir, "--database", db_name];

      const result = await executePython(
        getToolsDir("youtube_tools", "ingest_to_rag.py"),
        args,
        { pythonPath: config.python_path, timeout: 300_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error ingesting transcripts to "${db_name}":\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── youtube_analyze ──────────────────────────────────────────────────────
  server.tool(
    "youtube_analyze",
    "Analyze YouTube channel content using RAG-powered queries. Supports commands like topic analysis, content gaps, style comparison, and performance insights.",
    {
      command: z
        .string()
        .describe(
          'Analysis command to run (e.g., "topics", "gaps", "style", "compare", "summary")'
        ),
      database: z
        .string()
        .optional()
        .describe("RAG database to analyze. Defaults to the agent's default database."),
      query: z
        .string()
        .optional()
        .describe("Optional query to focus the analysis on a specific topic or question"),
    },
    async ({ command, database, query }) => {
      const db = database ?? config.default_rag_database;
      const args = ["--command", command, "--database", db];
      if (query) args.push("--query", query);

      const result = await executePython(
        getToolsDir("youtube_tools", "analyze_channels.py"),
        args,
        { pythonPath: config.python_path, timeout: 180_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error running analysis "${command}":\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── youtube_strategy ─────────────────────────────────────────────────────
  server.tool(
    "youtube_strategy",
    "Get YouTube strategy advice by querying a curated strategy knowledge base. Useful for content planning, SEO, thumbnail strategy, and audience growth.",
    {
      scenario: z
        .string()
        .describe(
          "Describe the scenario or question for strategy advice (e.g., 'how to improve CTR on relocation videos')"
        ),
      max_results: z
        .number()
        .int()
        .min(1)
        .max(20)
        .optional()
        .describe("Maximum number of strategy results to return (default: 5)"),
    },
    async ({ scenario, max_results }) => {
      const args = ["--query", scenario];
      if (max_results !== undefined) args.push("--k", String(max_results));

      const result = await executePython(
        getToolsDir("youtube_tools", "rag_youtube_helper.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error fetching strategy advice:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );
}
