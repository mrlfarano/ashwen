# Task Master Setup for Ashwen

Ashwen is pre-configured to use **Task Master AI** as both a CLI tool and an MCP server.

## Files added
- `.taskmaster/config.json` — Task Master model config
- `.taskmaster/docs/ashwen-prd.md` — PRD input for task generation
- `.mcp.json` — generic MCP config
- `.cursor/mcp.json` — Cursor/Windsurf MCP config
- `.vscode/mcp.json` — VS Code MCP config
- `.env.taskmaster.example` — environment variable template
- `.pi/extensions/taskmaster/` — project-local pi extension for Task Master CLI integration

## Model configuration
Current Task Master config is set to use a **local OpenAI-compatible endpoint** for all roles.

Chosen endpoint:
- `http://localhost:1234/v1`

Chosen model:
- `qwen3.5:9b`

Configured roles:
- main: `qwen3.5:9b`
- research: `qwen3.5:9b`
- fallback: `qwen3.5:9b`

## Authentication
This setup assumes your local server accepts OpenAI-compatible requests on:
- `http://localhost:1234/v1`

Configured local values:
- `OPENAI_API_KEY=local`
- `OPENAI_BASE_URL=http://localhost:1234/v1`

These values are stored in:
- `.env.taskmaster`
- `.mcp.json`
- `.cursor/mcp.json`
- `.vscode/mcp.json`

These files are ignored by `.gitignore` so local secrets/config do not get committed.

## Using Task Master via MCP
### Cursor / Windsurf
Use:
- `.cursor/mcp.json`

### VS Code
Use:
- `.vscode/mcp.json`

### Generic MCP clients
Use:
- `.mcp.json`

Task Master MCP server command:
```json
{
  "command": "npx",
  "args": ["-y", "task-master-ai"]
}
```

## CLI commands
If your environment has `npm` / `npx`, you can use the package scripts:

```bash
npm run taskmaster:init
npm run taskmaster:models
npm run taskmaster:parse-prd
npm run taskmaster:parse-prd:research
```

Equivalent direct commands:
```bash
npx -y task-master-ai init
npx -y task-master-ai models --setup
npx -y task-master-ai parse-prd .taskmaster/docs/ashwen-prd.md
npx -y task-master-ai parse-prd .taskmaster/docs/ashwen-prd.md --research
```

## Recommended workflow for Ashwen
1. Make sure your local server is running at `http://localhost:1234/v1`.
2. Make sure model `qwen3.5:9b` is available there.
3. Start Task Master through MCP in your editor or via the Task Master CLI.
4. Confirm the server or CLI is healthy.
5. Parse or expand tasks as needed.

## Using Task Master inside pi
This repo also includes a project-local pi extension at:
- `.pi/extensions/taskmaster/`

If pi is already running, use:
```bash
/reload
```

Then you can use commands like:
- `/taskmaster-list`
- `/taskmaster-next`
- `/taskmaster-expand-high`
- `/taskmaster-parse-prd`
- `/taskmaster-parse-prd-research`
- `/taskmaster expand --id 6 --force --research`

`/taskmaster-expand-high` runs an opinionated high-detail expansion preset equivalent to:
```bash
/taskmaster expand --all --force --research --num 8 --prompt "Expand tasks into high-complexity, implementation-ready subtasks with strong architecture, edge cases, validation, observability, migrations, failure handling, and thorough test coverage."
```

Or ask pi to use the Task Master tools directly.

## Notes
- The active setup no longer depends on Perplexity quota.
- The active setup no longer depends on Ollama Cloud auth.
- If your local endpoint uses a different auth token, replace `OPENAI_API_KEY=local` in the local ignored files.
