import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import {
  DEFAULT_MAX_BYTES,
  DEFAULT_MAX_LINES,
  formatSize,
  truncateHead,
  type TruncationResult,
} from "@mariozechner/pi-coding-agent";
import { Box, Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { spawn } from "node:child_process";

const DEFAULT_PRD_PATH = ".taskmaster/docs/ashwen-prd.md";
const ENV_FILE_NAME = ".env.taskmaster";

type TaskMasterParams = {
  args: string;
};

type ParsePrdParams = {
  prdPath?: string;
  research?: boolean;
};

interface TaskMasterRunResult {
  command: string;
  args: string[];
  cwd: string;
  exitCode: number;
  output: string;
  truncated?: TruncationResult;
  fullOutputPath?: string;
}

interface CandidateCommand {
  command: string;
  baseArgs?: string[];
  useShell?: boolean;
}

const IS_WINDOWS = process.platform === "win32";

function parseEnvFile(content: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key) env[key] = value;
  }
  return env;
}

function findUp(startDir: string, fileName: string): string | null {
  let current = resolve(startDir);
  while (true) {
    const candidate = join(current, fileName);
    if (existsSync(candidate)) return candidate;
    const parent = dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

function loadTaskMasterEnv(cwd: string): Record<string, string> {
  const envPath = findUp(cwd, ENV_FILE_NAME);
  if (!envPath) return {};
  try {
    return parseEnvFile(readFileSync(envPath, "utf8"));
  } catch {
    return {};
  }
}

function buildCandidates(cwd: string): CandidateCommand[] {
  const configured = process.env.TASKMASTER_COMMAND?.trim();
  const candidates: CandidateCommand[] = [];
  if (configured) {
    candidates.push({ command: configured, useShell: true });
  }

  const localBin = resolve(cwd, "node_modules", ".bin");

  if (IS_WINDOWS) {
    candidates.push(
      { command: join(localBin, "task-master.cmd"), useShell: true },
      { command: join(localBin, "task-master-ai.cmd"), useShell: true },
      { command: join(localBin, "task-master"), useShell: true },
      { command: join(localBin, "task-master-ai"), useShell: true },
      { command: "task-master.cmd", useShell: true },
      { command: "task-master-ai.cmd", useShell: true },
      { command: "task-master", useShell: true },
      { command: "task-master-ai", useShell: true },
      { command: "npx", baseArgs: ["-y", "task-master-ai"], useShell: true }
    );
  } else {
    candidates.push(
      { command: join(localBin, "task-master") },
      { command: join(localBin, "task-master.cmd") },
      { command: join(localBin, "task-master-ai") },
      { command: join(localBin, "task-master-ai.cmd") },
      { command: "task-master" },
      { command: "task-master.cmd" },
      { command: "task-master-ai" },
      { command: "task-master-ai.cmd" },
      { command: "npx", baseArgs: ["-y", "task-master-ai"] }
    );
  }

  return candidates;
}

function formatCommand(command: string, args: string[]): string {
  return [command, ...args].join(" ");
}

async function runCandidate(
  candidate: CandidateCommand,
  args: string[],
  cwd: string,
  env: Record<string, string>,
  signal?: AbortSignal
): Promise<{ code: number; output: string }> {
  return await new Promise((resolvePromise, rejectPromise) => {
    const child = spawn(candidate.command, [...(candidate.baseArgs ?? []), ...args], {
      cwd,
      env,
      shell: candidate.useShell ?? false,
      signal,
    });

    let stdout = "";
    let stderr = "";

    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", rejectPromise);
    child.on("close", (code) => {
      const output = [stdout.trim(), stderr.trim()].filter(Boolean).join("\n\n");
      resolvePromise({ code: code ?? 1, output });
    });
  });
}

function truncateOutput(output: string): { text: string; truncation?: TruncationResult; fullOutputPath?: string } {
  const truncation = truncateHead(output, {
    maxLines: DEFAULT_MAX_LINES,
    maxBytes: DEFAULT_MAX_BYTES,
  });

  if (!truncation.truncated) {
    return { text: truncation.content };
  }

  const tempDir = mkdtempSync(join(tmpdir(), "pi-taskmaster-"));
  const fullOutputPath = join(tempDir, "output.txt");
  writeFileSync(fullOutputPath, output, "utf8");

  let text = truncation.content;
  text += `\n\n[Output truncated: showing ${truncation.outputLines} of ${truncation.totalLines} lines`;
  text += ` (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)}).`;
  text += ` Full output saved to: ${fullOutputPath}]`;

  return { text, truncation, fullOutputPath };
}

async function runTaskMaster(args: string[], cwd: string, signal?: AbortSignal): Promise<TaskMasterRunResult> {
  const mergedEnv = { ...process.env, ...loadTaskMasterEnv(cwd) };
  const candidates = buildCandidates(cwd);
  const failures: string[] = [];

  for (const candidate of candidates) {
    try {
      const result = await runCandidate(candidate, args, cwd, mergedEnv, signal);
      const notFound =
        result.code === 127 ||
        /command not found|is not recognized as an internal or external command/i.test(result.output);

      if (notFound) {
        failures.push(`${formatCommand(candidate.command, [...(candidate.baseArgs ?? []), ...args])}: ${result.output || "not found"}`);
        continue;
      }

      const truncated = truncateOutput(result.output || "(no output)");
      return {
        command: candidate.command,
        args: [...(candidate.baseArgs ?? []), ...args],
        cwd,
        exitCode: result.code,
        output: truncated.text,
        truncated: truncated.truncation,
        fullOutputPath: truncated.fullOutputPath,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      failures.push(`${formatCommand(candidate.command, [...(candidate.baseArgs ?? []), ...args])}: ${message}`);
    }
  }

  throw new Error(
    `Unable to run Task Master. Tried: ${failures.join(" | ")}\n` +
      `If needed, set TASKMASTER_COMMAND to the exact executable or shell command. ` +
      `On Windows, a good fallback is: TASKMASTER_COMMAND=npx -y task-master-ai`
  );
}

function normalizePrdPath(cwd: string, prdPath?: string): string {
  const candidate = (prdPath || DEFAULT_PRD_PATH).trim();
  if (isAbsolute(candidate)) return candidate;
  return resolve(cwd, candidate);
}

function publishResult(pi: ExtensionAPI, type: "success" | "error", title: string, result: TaskMasterRunResult | { message: string }) {
  if ("message" in result) {
    pi.sendMessage({
      customType: "taskmaster-result",
      content: title,
      display: true,
      details: {
        type,
        title,
        message: result.message,
        timestamp: Date.now(),
      },
    });
    return;
  }

  pi.sendMessage({
    customType: "taskmaster-result",
    content: title,
    display: true,
    details: {
      type,
      title,
      command: formatCommand(result.command, result.args),
      cwd: result.cwd,
      exitCode: result.exitCode,
      output: result.output,
      fullOutputPath: result.fullOutputPath,
      timestamp: Date.now(),
    },
  });
}

function splitArgs(input: string): string[] {
  return input
    .trim()
    .match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g)?.map((part) => part.replace(/^['"]|['"]$/g, "")) ?? [];
}

const TASKMASTER_SUBCOMMANDS = [
  "list",
  "next",
  "parse-prd",
  "expand",
  "show",
  "set-status",
  "update-task",
  "models",
  "init",
] as const;

const HIGH_COMPLEXITY_EXPAND_PROMPT =
  "Expand tasks into high-complexity, implementation-ready subtasks with strong architecture, edge cases, validation, observability, migrations, failure handling, and thorough test coverage.";
const HIGH_COMPLEXITY_SUBTASK_COUNT = "8";

const TASKMASTER_STATUS_ID = "taskmaster-status";

function publishRunning(pi: ExtensionAPI, label: string) {
  pi.sendMessage({
    customType: "taskmaster-running",
    content: `Running Task Master: ${label}`,
    display: true,
    details: {
      label,
      timestamp: Date.now(),
    },
  });
}

async function withTaskMasterStatus<T>(
  pi: ExtensionAPI,
  ctx: { ui: { theme: any; setStatus: (id: string, text: string) => void } },
  label: string,
  action: () => Promise<T>
): Promise<T> {
  const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  let frame = 0;
  const render = () => {
    const theme = ctx.ui.theme;
    ctx.ui.setStatus(
      TASKMASTER_STATUS_ID,
      theme.fg("accent", spinnerFrames[frame]) + theme.fg("dim", ` Task Master: ${label}`)
    );
    frame = (frame + 1) % spinnerFrames.length;
  };

  publishRunning(pi, label);
  render();
  const timer = setInterval(render, 120);

  try {
    const result = await action();
    const theme = ctx.ui.theme;
    ctx.ui.setStatus(
      TASKMASTER_STATUS_ID,
      theme.fg("success", "✓") + theme.fg("dim", ` Task Master: ${label} complete`)
    );
    return result;
  } catch (error) {
    const theme = ctx.ui.theme;
    ctx.ui.setStatus(
      TASKMASTER_STATUS_ID,
      theme.fg("error", "✗") + theme.fg("dim", ` Task Master: ${label} failed`)
    );
    throw error;
  } finally {
    clearInterval(timer);
  }
}

export default function taskmasterExtension(pi: ExtensionAPI) {
  pi.registerMessageRenderer("taskmaster-running", (message, _options, theme) => {
    const details = message.details as { label?: string } | undefined;
    const text = `${theme.fg("accent", theme.bold("Running Task Master"))}\n${theme.fg("dim", details?.label || String(message.content))}`;
    const box = new Box(1, 1, (t) => theme.bg("customMessageBg", t));
    box.addChild(new Text(text, 0, 0));
    return box;
  });

  pi.registerMessageRenderer("taskmaster-result", (message, { expanded }, theme) => {
    const details = message.details as
      | {
          type: "success" | "error";
          title: string;
          message?: string;
          command?: string;
          cwd?: string;
          exitCode?: number;
          output?: string;
          fullOutputPath?: string;
          timestamp?: number;
        }
      | undefined;

    const isError = details?.type === "error";
    const color = isError ? "error" : "success";
    let text = `${theme.fg(color, theme.bold(details?.title || String(message.content)))}\n`;

    if (details?.message) {
      text += details.message;
    } else {
      if (details?.command) text += `${theme.fg("dim", `Command: ${details.command}`)}\n`;
      if (details?.cwd) text += `${theme.fg("dim", `CWD: ${details.cwd}`)}\n`;
      if (details?.exitCode !== undefined) text += `${theme.fg("dim", `Exit code: ${details.exitCode}`)}\n`;
      if (details?.output) {
        text += `\n${details.output}`;
      }
      if (details?.fullOutputPath) {
        text += `\n${theme.fg("muted", `Full output: ${details.fullOutputPath}`)}`;
      }
    }

    const box = new Box(1, 1, (t) => theme.bg("customMessageBg", t));
    box.addChild(new Text(text.trimEnd(), 0, 0));
    return box;
  });

  pi.registerCommand("taskmaster", {
    description: "Run Task Master CLI with arbitrary arguments, e.g. /taskmaster list",
    getArgumentCompletions: (prefix) => {
      const trimmed = prefix.trim();
      if (trimmed.includes(" ")) return null;
      return TASKMASTER_SUBCOMMANDS.filter((value) => value.startsWith(trimmed)).map((value) => ({ value, label: value }));
    },
    handler: async (args, ctx) => {
      const parsedArgs = splitArgs(args);
      if (parsedArgs.length === 0) {
        publishResult(pi, "error", "Task Master command failed", {
          message: "Usage: /taskmaster <args>. Example: /taskmaster list",
        });
        return;
      }
      try {
        const result = await withTaskMasterStatus(pi, ctx, parsedArgs.join(" "), () => runTaskMaster(parsedArgs, ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", `Task Master: ${parsedArgs.join(" ")}`, result);
      } catch (error) {
        publishResult(pi, "error", "Task Master command failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-list", {
    description: "Show Task Master task list",
    handler: async (_args, ctx) => {
      try {
        const result = await withTaskMasterStatus(pi, ctx, "list", () => runTaskMaster(["list"], ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", "Task Master task list", result);
      } catch (error) {
        publishResult(pi, "error", "Task Master list failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-next", {
    description: "Show the next Task Master task",
    handler: async (_args, ctx) => {
      try {
        const result = await withTaskMasterStatus(pi, ctx, "next", () => runTaskMaster(["next"], ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", "Task Master next task", result);
      } catch (error) {
        publishResult(pi, "error", "Task Master next failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-expand-all", {
    description: "Expand all Task Master tasks into subtasks",
    handler: async (_args, ctx) => {
      try {
        const result = await withTaskMasterStatus(pi, ctx, "expand --all", () => runTaskMaster(["expand", "--all"], ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", "Task Master expand --all", result);
      } catch (error) {
        publishResult(pi, "error", "Task Master expand failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-expand-high", {
    description: "Expand all tasks with high-complexity, implementation-ready subtasks",
    handler: async (_args, ctx) => {
      const commandArgs = [
        "expand",
        "--all",
        "--force",
        "--research",
        "--num",
        HIGH_COMPLEXITY_SUBTASK_COUNT,
        "--prompt",
        HIGH_COMPLEXITY_EXPAND_PROMPT,
      ];
      try {
        const result = await withTaskMasterStatus(pi, ctx, "expand --all --force --research --num 8", () =>
          runTaskMaster(commandArgs, ctx.cwd)
        );
        publishResult(pi, result.exitCode === 0 ? "success" : "error", "Task Master high-complexity expand --all", result);
      } catch (error) {
        publishResult(pi, "error", "Task Master high-complexity expand failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-parse-prd", {
    description: "Parse a PRD into Task Master tasks. Usage: /taskmaster-parse-prd [path]",
    handler: async (args, ctx) => {
      try {
        const prdPath = normalizePrdPath(ctx.cwd, args.trim() || DEFAULT_PRD_PATH);
        const result = await withTaskMasterStatus(pi, ctx, `parse-prd ${prdPath}`, () => runTaskMaster(["parse-prd", prdPath], ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", `Task Master parse PRD: ${prdPath}`, result);
      } catch (error) {
        publishResult(pi, "error", "Task Master parse-prd failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerCommand("taskmaster-parse-prd-research", {
    description: "Parse a PRD into Task Master tasks with research. Usage: /taskmaster-parse-prd-research [path]",
    handler: async (args, ctx) => {
      try {
        const prdPath = normalizePrdPath(ctx.cwd, args.trim() || DEFAULT_PRD_PATH);
        const result = await withTaskMasterStatus(pi, ctx, `parse-prd ${prdPath} --research`, () => runTaskMaster(["parse-prd", prdPath, "--research"], ctx.cwd));
        publishResult(pi, result.exitCode === 0 ? "success" : "error", `Task Master parse PRD with research: ${prdPath}`, result);
      } catch (error) {
        publishResult(pi, "error", "Task Master parse-prd --research failed", {
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  pi.registerTool({
    name: "taskmaster_list",
    label: "Task Master List",
    description: "List Task Master tasks for the current project.",
    promptSnippet: "List the current Task Master tasks for this project.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal, _onUpdate, ctx) {
      const result = await runTaskMaster(["list"], ctx.cwd, signal);
      if (result.exitCode !== 0) {
        throw new Error(result.output);
      }
      return {
        content: [{ type: "text", text: result.output }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "taskmaster_next",
    label: "Task Master Next",
    description: "Show the next Task Master task based on status and dependencies.",
    promptSnippet: "Show the next Task Master task to work on.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal, _onUpdate, ctx) {
      const result = await runTaskMaster(["next"], ctx.cwd, signal);
      if (result.exitCode !== 0) {
        throw new Error(result.output);
      }
      return {
        content: [{ type: "text", text: result.output }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "taskmaster_parse_prd",
    label: "Task Master Parse PRD",
    description: `Parse a PRD into Task Master tasks. Defaults to ${DEFAULT_PRD_PATH}.`,
    promptSnippet: "Parse a PRD into Task Master tasks, optionally with research enabled.",
    parameters: Type.Object({
      prdPath: Type.Optional(Type.String({ description: `Path to PRD file. Defaults to ${DEFAULT_PRD_PATH}` })),
      research: Type.Optional(Type.Boolean({ description: "Whether to add --research" })),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const typed = params as ParsePrdParams;
      const prdPath = normalizePrdPath(ctx.cwd, typed.prdPath || DEFAULT_PRD_PATH);
      const args = ["parse-prd", prdPath];
      if (typed.research) args.push("--research");
      const result = await runTaskMaster(args, ctx.cwd, signal);
      if (result.exitCode !== 0) {
        throw new Error(result.output);
      }
      return {
        content: [{ type: "text", text: result.output }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "taskmaster_run",
    label: "Task Master Run",
    description: "Run arbitrary Task Master CLI arguments when the dedicated tools do not cover the needed command.",
    promptSnippet: "Run arbitrary Task Master CLI arguments if a dedicated Task Master tool is not sufficient.",
    promptGuidelines: [
      "Prefer the dedicated Task Master tools for listing tasks, finding the next task, and parsing PRDs.",
      "Use this only for other Task Master subcommands such as expand, update-task, or set-status.",
    ],
    parameters: Type.Object({
      args: Type.String({ description: 'Task Master CLI arguments, e.g. "expand --all" or "set-status --id=3 --status=done"' }),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const typed = params as TaskMasterParams;
      const args = splitArgs(typed.args);
      if (args.length === 0) {
        throw new Error("No Task Master arguments provided.");
      }
      const result = await runTaskMaster(args, ctx.cwd, signal);
      if (result.exitCode !== 0) {
        throw new Error(result.output);
      }
      return {
        content: [{ type: "text", text: result.output }],
        details: result,
      };
    },
  });

  pi.on("session_start", async (_event, ctx) => {
    const envPath = findUp(ctx.cwd, ENV_FILE_NAME);
    const commandHint = process.env.TASKMASTER_COMMAND ? `TASKMASTER_COMMAND=${process.env.TASKMASTER_COMMAND}` : "default command resolution";
    ctx.ui.notify(
      `Task Master extension loaded (${commandHint}${envPath ? `, env: ${envPath}` : ""})`,
      "info"
    );
  });
}
