# Ashwen Product & Desktop Architecture

## Product vision
Ashwen is an AI-assisted software development workspace that starts as a strong desktop experience for individual builders and grows into a collaborative SaaS for engineering teams.

The long-term ambition is not just to be a coding chat app, but to become:
- a **shared memory layer** for software teams
- a **multi-agent workspace** for planning, building, reviewing, and debugging
- a **system of record for technical decisions, project context, and agent-assisted execution**

## Product goal
Turn Ashwen into a cross-platform desktop app for Windows and macOS while keeping the current Python backend and Svelte UI, then expand it into a SaaS with cloud sync, collaboration, team workspaces, and enterprise deployment options.

## Core product thesis
Ashwen should help teams answer questions like:
- What are we building and why?
- What did we already decide?
- Which files, services, and systems are affected by this change?
- Which agent or teammate should act next?
- How do we retain project knowledge across sessions, contributors, and time?

## Desktop-first architecture
- **Electron shell** hosts the desktop app window.
- **Svelte frontend** is built as static assets and loaded by Electron.
- **FastAPI backend** runs as a local sidecar process on `127.0.0.1:8000`.
- **SQLite + encrypted credentials** live in the user's app data directory.
- **GitHub Releases + electron-updater** provide in-app auto-updates.

## Why this is the right move
- Preserves the existing backend investment instead of rewriting everything in Node.
- Makes desktop packaging practical with `electron-builder`.
- Supports fast iteration now and a larger multi-user installed base later.
- Keeps future options open for cloud sync, collaboration, telemetry, and enterprise deployment.
- Lets Ashwen win first on local reliability and UX before layering in cloud and team features.

## Target users
### Initial users
- solo founders
- indie hackers
- technical product builders
- engineers working across multiple repos and tools

### Expansion users
- startup engineering teams
- product squads
- agencies and studios
- platform and architecture teams
- enterprise engineering orgs that need auditability and knowledge retention

## Key product pillars
1. **AI-native project workspace**
   - Projects, agents, chats, memory, and settings live in one place.
2. **Persistent memory**
   - Decisions, patterns, context, and learnings survive beyond chat sessions.
3. **Multi-agent collaboration**
   - Specialized agents assist with architecture, UI, APIs, review, debugging, and operations.
4. **Developer workflow integration**
   - Git, issues, PRs, and docs should connect directly to the workspace.
5. **Team and cloud layer**
   - Shared projects, synced memory, and async collaboration expand Ashwen into a true SaaS.

## Release flow
1. Push a tag like `v0.1.0`.
2. GitHub Actions builds macOS and Windows artifacts.
3. `electron-builder` publishes installers to GitHub Releases.
4. Installed apps detect and download updates automatically.
5. Users restart once to apply the update.

## Roadmap

### Phase 1 — Desktop MVP foundation
- Harden Electron startup and packaging.
- Add code signing for macOS and Windows production builds.
- Add crash reporting and product analytics.
- Add a first-run onboarding flow for credentials and local model setup.
- Improve local project management, memory, and WebSocket reliability.

### Phase 2 — Core product differentiation
- Expand agent orchestration and background task execution.
- Improve memory capture, search, and retrieval quality.
- Add richer project context management and decision history.
- Add review workflows for architecture, API, and UI quality.
- Add source-aware context tied to files, modules, and recent work.

### Phase 3 — SaaS expansion
- Add **organizations and team workspaces**.
- Add **cloud accounts** and sync for projects, memories, and agent state.
- Add **shared threads** and async collaboration.
- Add **private vs shared memory scopes**.
- Add **usage analytics** and workspace-level visibility.

### Phase 4 — Integration ecosystem
- Add **GitHub/GitLab integration** for repos, pull requests, issues, and change summaries.
- Add **Jira / Linear / Notion integration** for turning conversations into work items.
- Add **Slack / Teams integration** for summaries, mentions, and agent workflows.
- Add **project templates and team playbooks**.
- Add **credential vault / provider management** for teams.

### Phase 5 — Advanced intelligence layer
- Add a **project knowledge graph** connecting code, systems, owners, incidents, and decisions.
- Add **impact analysis** and “what changed?” awareness.
- Add **explainability / observability** for agent outputs, memory sources, and model decisions.
- Add **background agents** for review, planning, debugging, and release readiness.
- Add a **decision log** and institutional memory views for teams.

### Phase 6 — Enterprise readiness
- Add SSO / SAML and SCIM provisioning.
- Add audit logs and retention controls.
- Add data residency and private deployment options.
- Add BYO model/provider routing policies.
- Add admin controls for usage, access, and compliance.

## Recommended SaaS features
These are the highest-value SaaS additions Ashwen should prioritize as the product matures.

### 1. Organizations and team workspaces
- shared workspaces
- workspace roles and permissions
- project-level access control
- owner/admin/member/viewer roles

### 2. Cloud-synced memory
- sync decisions, learnings, and project context across devices
- private vs shared memory
- searchable team knowledge base
- persistent decision history

### 3. GitHub/GitLab integrations
- repo connection
- pull request summaries
- issue linking
- commit-aware context
- branch-aware workspace state

### 4. Shared threads and async collaboration
- share conversations with teammates
- comment on agent outputs
- mention collaborators
- hand off threads across people and roles

### 5. Background multi-agent execution
- assign longer tasks to agents
- architecture review agent
- code review agent
- debugging and release-readiness agents
- async task history and result playback

### 6. Project knowledge graph
- connect files, services, systems, decisions, and owners
- support dependency understanding and impact analysis
- make project context durable and explorable

### 7. Review and governance workflows
- architecture review
- security review
- API review
- UI review
- release checklists and risk summaries

### 8. Admin analytics and ROI reporting
- workspace adoption metrics
- agent usage by workflow type
- decisions captured over time
- memory retrieval effectiveness
- time-saved and activity summaries

### 9. Secure team credential management
- workspace provider credentials
- encrypted vault behavior
- provider policy management
- audit trail for secrets changes

### 10. Enterprise controls
- SSO
- audit logs
- retention policies
- private deployment
- compliance-oriented controls

## Product positioning
Ashwen should position itself as:

> **The shared memory and multi-agent operating layer for software teams.**

That is stronger and more defensible than positioning it as a generic AI coding chat app.
