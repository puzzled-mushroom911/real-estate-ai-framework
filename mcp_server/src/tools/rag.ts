/**
 * RAG (Retrieval-Augmented Generation) query tools.
 * Wraps Python RAG scripts for knowledge base querying, multi-db queries,
 * listing databases, and creating new knowledge bases.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { executePython } from "../utils/python.js";
import { getConfig, getToolsDir, getKnowledgeBasesDir } from "../utils/config.js";

export function registerRagTools(server: McpServer): void {
  const config = getConfig();

  // ── rag_query ────────────────────────────────────────────────────────────
  server.tool(
    "rag_query",
    "Query a single RAG knowledge base with a natural language question. Returns the top-k most relevant chunks from the specified database.",
    {
      query: z.string().describe("Natural language query to search the knowledge base"),
      database: z
        .string()
        .optional()
        .describe("Name of the database to query. Defaults to the agent's default database."),
      k: z
        .number()
        .int()
        .min(1)
        .max(50)
        .optional()
        .describe("Number of results to return (default: 5)"),
    },
    async ({ query, database, k }) => {
      const db = database ?? config.default_rag_database;
      const args = ["--query", query, "--database", db];
      if (k !== undefined) args.push("--k", String(k));

      const result = await executePython(
        getToolsDir("rag_tools", "rag_query.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return { content: [{ type: "text" as const, text: `Error querying RAG database "${db}":\n${result.stderr}` }], isError: true };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── rag_query_multi ──────────────────────────────────────────────────────
  server.tool(
    "rag_query_multi",
    "Query multiple RAG knowledge bases simultaneously and return merged results. Useful for cross-referencing information across databases.",
    {
      query: z.string().describe("Natural language query to search across databases"),
      databases: z
        .array(z.string())
        .min(1)
        .describe("List of database names to query"),
      k: z
        .number()
        .int()
        .min(1)
        .max(50)
        .optional()
        .describe("Number of results per database (default: 5)"),
    },
    async ({ query, databases, k }) => {
      const args = ["--query", query, "--databases", ...databases];
      if (k !== undefined) args.push("--k", String(k));

      const result = await executePython(
        getToolsDir("rag_tools", "rag_query_multi.py"),
        args,
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return { content: [{ type: "text" as const, text: `Error querying multiple databases:\n${result.stderr}` }], isError: true };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── rag_list_databases ───────────────────────────────────────────────────
  server.tool(
    "rag_list_databases",
    "List all registered RAG knowledge base databases with their metadata (document count, last updated, description).",
    {},
    async () => {
      const result = await executePython(
        getToolsDir("rag_tools", "rag_system_manager.py"),
        ["list"],
        { pythonPath: config.python_path }
      );

      if (result.exitCode !== 0) {
        return { content: [{ type: "text" as const, text: `Error listing databases:\n${result.stderr}` }], isError: true };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );

  // ── rag_create_knowledge_base ────────────────────────────────────────────
  server.tool(
    "rag_create_knowledge_base",
    "Create a new RAG knowledge base by indexing documents from a source directory. Supports text, markdown, PDF, and transcript files.",
    {
      source_dir: z.string().describe("Path to directory containing source documents to index"),
      name: z.string().describe("Name for the new knowledge base"),
      chunk_size: z
        .number()
        .int()
        .min(100)
        .max(10000)
        .optional()
        .describe("Chunk size in characters for document splitting (default: 1000)"),
    },
    async ({ source_dir, name, chunk_size }) => {
      const args = ["create", "--source", source_dir, "--name", name];
      if (chunk_size !== undefined) args.push("--chunk-size", String(chunk_size));

      const result = await executePython(
        getToolsDir("rag_tools", "rag_system_manager.py"),
        args,
        { pythonPath: config.python_path, timeout: 300_000 }
      );

      if (result.exitCode !== 0) {
        return { content: [{ type: "text" as const, text: `Error creating knowledge base "${name}":\n${result.stderr}` }], isError: true };
      }
      return { content: [{ type: "text" as const, text: result.stdout }] };
    }
  );
}
