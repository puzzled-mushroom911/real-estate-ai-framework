/**
 * Python script execution utility.
 * Spawns Python child processes and captures structured output.
 */

import { spawn } from "node:child_process";
import { resolve } from "node:path";

export interface PythonResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export interface PythonOptions {
  /** Working directory for the script. Defaults to script's parent directory. */
  cwd?: string;
  /** Timeout in milliseconds. Defaults to 120000 (2 minutes). */
  timeout?: number;
  /** Additional environment variables merged with process.env. */
  env?: Record<string, string>;
  /** Python executable path. Defaults to "python3". */
  pythonPath?: string;
}

/**
 * Execute a Python script as a child process and return captured output.
 */
export async function executePython(
  scriptPath: string,
  args: string[] = [],
  options: PythonOptions = {}
): Promise<PythonResult> {
  const {
    cwd,
    timeout = 120_000,
    env: extraEnv = {},
    pythonPath = "python3",
  } = options;

  const resolvedScript = resolve(scriptPath);
  const workingDir = cwd ?? resolve(resolvedScript, "..");

  return new Promise<PythonResult>((resolvePromise, reject) => {
    const child = spawn(pythonPath, [resolvedScript, ...args], {
      cwd: workingDir,
      env: { ...process.env, ...extraEnv },
      stdio: ["ignore", "pipe", "pipe"],
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    child.stdout.on("data", (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderrChunks.push(chunk));

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(
        new Error(
          `Python script timed out after ${timeout}ms: ${resolvedScript}`
        )
      );
    }, timeout);

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(
        new Error(
          `Failed to spawn Python process for ${resolvedScript}: ${err.message}`
        )
      );
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      resolvePromise({
        stdout: Buffer.concat(stdoutChunks).toString("utf-8"),
        stderr: Buffer.concat(stderrChunks).toString("utf-8"),
        exitCode: code ?? 1,
      });
    });
  });
}

/**
 * Execute a Python script and parse JSON output.
 * Appends --json flag automatically so the script knows to output JSON.
 */
export async function executePythonJson<T = unknown>(
  scriptPath: string,
  args: string[] = [],
  options: PythonOptions = {}
): Promise<T> {
  const result = await executePython(scriptPath, [...args, "--json"], options);

  if (result.exitCode !== 0) {
    throw new Error(
      `Python script failed (exit ${result.exitCode}): ${result.stderr || result.stdout}`
    );
  }

  try {
    return JSON.parse(result.stdout) as T;
  } catch {
    throw new Error(
      `Failed to parse JSON output from ${scriptPath}. Raw output:\n${result.stdout}`
    );
  }
}
