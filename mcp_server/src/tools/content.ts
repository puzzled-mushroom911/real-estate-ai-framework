/**
 * Content generation tools.
 * Wraps Python scripts for converting transcripts to blog posts
 * and generating email sequences from content.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { executePython } from "../utils/python.js";
import { getConfig, getToolsDir } from "../utils/config.js";

export function registerContentTools(server: McpServer): void {
  const config = getConfig();

  // ── content_transcript_to_blog ───────────────────────────────────────────
  server.tool(
    "content_transcript_to_blog",
    "Convert a video transcript into a structured blog post. Extracts key points, organizes into sections with headings, and formats for web publishing.",
    {
      transcript_path: z
        .string()
        .describe("Path to the transcript file (text or JSON format)"),
      title: z
        .string()
        .optional()
        .describe("Blog post title. If omitted, one will be generated from the content."),
      agent_name: z
        .string()
        .optional()
        .describe("Agent name for voice/style matching. Defaults to configured agent."),
    },
    async ({ transcript_path, title, agent_name }) => {
      const args = ["--input", transcript_path];
      if (title) args.push("--title", title);
      if (agent_name) args.push("--agent", agent_name);

      const result = await executePython(
        getToolsDir("content_tools", "transcript_to_blog.py"),
        args,
        { pythonPath: config.python_path, timeout: 180_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error converting transcript to blog:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── content_generate_emails ──────────────────────────────────────────────
  server.tool(
    "content_generate_emails",
    "Generate email templates from source content. Creates nurture sequences, follow-ups, or drip campaign emails based on video or blog content.",
    {
      source_path: z
        .string()
        .describe("Path to the source content file (transcript, blog post, or guide)"),
      sequence_type: z
        .enum(["nurture", "followup", "drip", "welcome", "reengagement"])
        .optional()
        .describe('Type of email sequence to generate (default: "nurture")'),
      count: z
        .number()
        .int()
        .min(1)
        .max(20)
        .optional()
        .describe("Number of emails to generate in the sequence (default: 5)"),
    },
    async ({ source_path, sequence_type, count }) => {
      const args = ["--input", source_path];
      if (sequence_type) args.push("--type", sequence_type);
      if (count !== undefined) args.push("--count", String(count));

      const result = await executePython(
        getToolsDir("content_tools", "generate_emails.py"),
        args,
        { pythonPath: config.python_path, timeout: 180_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error generating email templates:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );
}
