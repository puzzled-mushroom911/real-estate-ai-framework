/**
 * CRM operation tools.
 * Wraps Python scripts for searching contacts, sending messages,
 * and retrieving conversation history from the CRM system.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { executePython } from "../utils/python.js";
import { getConfig, getToolsDir } from "../utils/config.js";

export function registerCrmTools(server: McpServer): void {
  const config = getConfig();

  // ── crm_search_contacts ──────────────────────────────────────────────────
  server.tool(
    "crm_search_contacts",
    "Search CRM contacts by name, email, phone, tag, or free-text query. Returns matching contact records with key fields.",
    {
      query: z
        .string()
        .describe("Search query - can be a name, email, phone number, tag, or keyword"),
      limit: z
        .number()
        .int()
        .min(1)
        .max(100)
        .optional()
        .describe("Maximum number of contacts to return (default: 10)"),
    },
    async ({ query, limit }) => {
      const args = ["search", "--query", query];
      if (limit !== undefined) args.push("--limit", String(limit));

      const result = await executePython(
        getToolsDir("crm_tools", "crm_operations.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error searching contacts:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── crm_send_message ─────────────────────────────────────────────────────
  server.tool(
    "crm_send_message",
    "Send an SMS or email message to a CRM contact. Requires the contact ID and message content.",
    {
      contact_id: z
        .string()
        .describe("CRM contact ID to send the message to"),
      message: z
        .string()
        .describe("Message body to send"),
      type: z
        .enum(["sms", "email"])
        .optional()
        .describe('Message type: "sms" or "email" (default: "sms")'),
    },
    async ({ contact_id, message, type }) => {
      const args = ["send", "--contact", contact_id, "--message", message];
      if (type) args.push("--type", type);

      const result = await executePython(
        getToolsDir("crm_tools", "crm_operations.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error sending message:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── crm_get_conversations ────────────────────────────────────────────────
  server.tool(
    "crm_get_conversations",
    "Retrieve conversation history for a CRM contact. Returns messages across all channels (SMS, email, etc.) in chronological order.",
    {
      contact_id: z
        .string()
        .describe("CRM contact ID to retrieve conversations for"),
    },
    async ({ contact_id }) => {
      const args = ["conversations", "--contact", contact_id];

      const result = await executePython(
        getToolsDir("crm_tools", "crm_operations.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error retrieving conversations:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );
}
