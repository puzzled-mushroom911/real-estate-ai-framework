/**
 * Configuration loader for the MCP server.
 * Reads agent profile and directory settings from env vars, YAML files, or defaults.
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve, join } from "node:path";
import { homedir } from "node:os";
import { parse as parseYaml } from "yaml";

export interface AgentConfig {
  agent_name: string;
  brokerage: string;
  market_area: string;
  tools_dir: string;
  knowledge_bases_dir: string;
  python_path: string;
  default_rag_database: string;
  [key: string]: unknown;
}

const DEFAULT_CONFIG: AgentConfig = {
  agent_name: "agent",
  brokerage: "",
  market_area: "",
  tools_dir: resolve(import.meta.dirname, "..", "..", "..", "tools"),
  knowledge_bases_dir: resolve(
    import.meta.dirname,
    "..",
    "..",
    "..",
    "knowledge_bases"
  ),
  python_path: "python3",
  default_rag_database: "general",
};

let _config: AgentConfig | null = null;

function loadConfigFromFile(filePath: string): Partial<AgentConfig> {
  if (!existsSync(filePath)) return {};
  try {
    const raw = readFileSync(filePath, "utf-8");
    return (parseYaml(raw) as Partial<AgentConfig>) ?? {};
  } catch {
    return {};
  }
}

/**
 * Load and cache configuration.
 * Priority: environment variables > AGENT_PROFILE path > ~/.real_estate_ai/agent_profile.yaml > project config > defaults.
 */
export function getConfig(): AgentConfig {
  if (_config) return _config;

  // Layer 1: defaults
  let merged: AgentConfig = { ...DEFAULT_CONFIG };

  // Layer 2: project-local config
  const projectConfig = resolve(
    import.meta.dirname,
    "..",
    "..",
    "config",
    "agent_profile.yaml"
  );
  merged = { ...merged, ...loadConfigFromFile(projectConfig) };

  // Layer 3: user home config
  const homeConfig = join(homedir(), ".real_estate_ai", "agent_profile.yaml");
  merged = { ...merged, ...loadConfigFromFile(homeConfig) };

  // Layer 4: explicit AGENT_PROFILE env var path
  const envProfile = process.env.AGENT_PROFILE;
  if (envProfile) {
    merged = { ...merged, ...loadConfigFromFile(resolve(envProfile)) };
  }

  // Layer 5: individual env var overrides
  if (process.env.TOOLS_DIR) merged.tools_dir = process.env.TOOLS_DIR;
  if (process.env.KNOWLEDGE_BASES_DIR)
    merged.knowledge_bases_dir = process.env.KNOWLEDGE_BASES_DIR;
  if (process.env.PYTHON_PATH) merged.python_path = process.env.PYTHON_PATH;
  if (process.env.AGENT_NAME) merged.agent_name = process.env.AGENT_NAME;
  if (process.env.DEFAULT_RAG_DATABASE)
    merged.default_rag_database = process.env.DEFAULT_RAG_DATABASE;

  _config = merged;
  return _config;
}

/** Resolve a path within the tools directory. */
export function getToolsDir(...segments: string[]): string {
  return resolve(getConfig().tools_dir, ...segments);
}

/** Resolve a path within the knowledge bases directory. */
export function getKnowledgeBasesDir(...segments: string[]): string {
  return resolve(getConfig().knowledge_bases_dir, ...segments);
}

/** Reset cached config (useful for testing). */
export function resetConfig(): void {
  _config = null;
}
