/**
 * CSV processing tools.
 * Wraps Python scripts for cleaning/validating contact CSVs
 * and importing conversation data into RAG databases.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { executePython } from "../utils/python.js";
import { getConfig, getToolsDir } from "../utils/config.js";

export function registerCsvTools(server: McpServer): void {
  const config = getConfig();

  // ── csv_process_contacts ─────────────────────────────────────────────────
  server.tool(
    "csv_process_contacts",
    "Clean and validate a contact CSV file. Can deduplicate records, validate email/phone formats, normalize fields, and output a cleaned CSV ready for CRM import.",
    {
      input_path: z
        .string()
        .describe("Path to the input CSV file containing contact data"),
      dedupe: z
        .boolean()
        .optional()
        .describe("Remove duplicate contacts based on email/phone (default: true)"),
      validate: z
        .boolean()
        .optional()
        .describe("Validate email and phone number formats (default: true)"),
    },
    async ({ input_path, dedupe, validate }) => {
      const args = ["--input", input_path];
      if (dedupe === false) args.push("--no-dedupe");
      if (validate === false) args.push("--no-validate");

      const result = await executePython(
        getToolsDir("csv_tools", "process_contacts.py"),
        args,
        { pythonPath: config.python_path, timeout: 180_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error processing contacts CSV:\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── csv_import_conversations ─────────────────────────────────────────────
  server.tool(
    "csv_import_conversations",
    "Import conversation data from a CSV file into a RAG knowledge base. Each row becomes a searchable document for later retrieval.",
    {
      csv_path: z
        .string()
        .describe("Path to the CSV file containing conversation data"),
      db_name: z
        .string()
        .describe("Name of the RAG database to import conversations into"),
    },
    async ({ csv_path, db_name }) => {
      const args = ["--input", csv_path, "--database", db_name];

      const result = await executePython(
        getToolsDir("csv_tools", "import_conversations.py"),
        args,
        { pythonPath: config.python_path, timeout: 300_000 }
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Error importing conversations to "${db_name}":\n${result.stderr}` }],
          isError: true,
        };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );
}
