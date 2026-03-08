# Project-local pi resources

This project includes a project-local pi extension:

- `.pi/extensions/taskmaster/`

## Task Master extension
The Task Master extension adds:
- `/taskmaster <args>`
- `/taskmaster-list`
- `/taskmaster-next`
- `/taskmaster-expand-all`
- `/taskmaster-expand-high`
- `/taskmaster-parse-prd [path]`
- `/taskmaster-parse-prd-research [path]`

It also registers LLM-callable tools:
- `taskmaster_list`
- `taskmaster_next`
- `taskmaster_parse_prd`
- `taskmaster_run`

## Notes
- The extension will try to find Task Master in this order:
  1. `TASKMASTER_COMMAND` env var
  2. `task-master`
  3. `task-master.cmd`
  4. `task-master-ai`
  5. `task-master-ai.cmd`
  6. `npx -y task-master-ai`
- It also loads environment variables from `.env.taskmaster` if present.
- It checks project-local `node_modules/.bin` before falling back to PATH and `npx`.
- If pi is already running, use `/reload` after adding or editing the extension.
