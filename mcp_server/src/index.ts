#!/usr/bin/env node

/**
 * Real Estate Agent AI Framework — MCP Server
 *
 * A Model Context Protocol server that wraps Python-based tools for:
 *   - RAG knowledge base queries (single, multi-db, create, list)
 *   - YouTube transcript fetching, ingestion, analysis, and strategy
 *   - Content generation (transcript-to-blog, email sequences)
 *   - CRM operations (search, message, conversations)
 *   - CSV processing (contact cleaning, conversation import)
 *
 * Communicates via stdio transport so Claude Code (or any MCP client)
 * can call these tools directly.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { getConfig } from "./utils/config.js";
import { registerRagTools } from "./tools/rag.js";
import { registerYoutubeTools } from "./tools/youtube.js";
import { registerContentTools } from "./tools/content.js";
import { registerCrmTools } from "./tools/crm.js";
import { registerCsvTools } from "./tools/csv.js";
// Guide tools removed — relocation guide generation is now a separate add-on

// ── Server bootstrap ───────────────────────────────────────────────────────

const SERVER_NAME = "real-estate-agent-mcp";
const SERVER_VERSION = "1.0.0";

async function main(): Promise<void> {
  // Load configuration early so tool registrations can reference it
  const config = getConfig();

  // Create the MCP server
  const server = new McpServer(
    {
      name: SERVER_NAME,
      version: SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // ── Register all tool groups ───────────────────────────────────────────

  registerRagTools(server);
  registerYoutubeTools(server);
  registerContentTools(server);
  registerCrmTools(server);
  registerCsvTools(server);

  // ── Connect via stdio transport ────────────────────────────────────────

  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Log startup to stderr (stdout is reserved for MCP protocol messages)
  console.error(
    `[${SERVER_NAME}] v${SERVER_VERSION} started — agent: ${config.agent_name}, tools: ${config.tools_dir}`
  );
}

// ── Entry point ────────────────────────────────────────────────────────────

main().catch((err) => {
  console.error(`[${SERVER_NAME}] Fatal error:`, err);
  process.exit(1);
});
