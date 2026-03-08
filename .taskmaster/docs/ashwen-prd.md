# Ashwen Product Requirements Document

Source of truth: `docs/desktop-architecture.md`

## Product vision
Ashwen is an AI-assisted software development workspace that starts as a strong desktop experience for individual builders and grows into a collaborative SaaS for engineering teams.

The long-term ambition is not just to be a coding chat app, but to become:
- a shared memory layer for software teams
- a multi-agent workspace for planning, building, reviewing, and debugging
- a system of record for technical decisions, project context, and agent-assisted execution

## Product goal
Turn Ashwen into a cross-platform desktop app for Windows and macOS while keeping the current Python backend and Svelte UI, then expand it into a SaaS with cloud sync, collaboration, team workspaces, and enterprise deployment options.

## Core product thesis
Ashwen should help teams answer questions like:
- What are we building and why?
- What did we already decide?
- Which files, services, and systems are affected by this change?
- Which agent or teammate should act next?
- How do we retain project knowledge across sessions, contributors, and time?

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
1. AI-native project workspace
2. Persistent memory
3. Multi-agent collaboration
4. Developer workflow integration
5. Team and cloud layer

## Phase 1 — Desktop MVP foundation
- Harden Electron startup and packaging.
- Add code signing for macOS and Windows production builds.
- Add crash reporting and product analytics.
- Add a first-run onboarding flow for credentials and local model setup.
- Improve local project management, memory, and WebSocket reliability.

## Phase 2 — Core product differentiation
- Expand agent orchestration and background task execution.
- Improve memory capture, search, and retrieval quality.
- Add richer project context management and decision history.
- Add review workflows for architecture, API, and UI quality.
- Add source-aware context tied to files, modules, and recent work.

## Phase 3 — SaaS expansion
- Add organizations and team workspaces.
- Add cloud accounts and sync for projects, memories, and agent state.
- Add shared threads and async collaboration.
- Add private vs shared memory scopes.
- Add usage analytics and workspace-level visibility.

## Phase 4 — Integration ecosystem
- Add GitHub/GitLab integration for repos, pull requests, issues, and change summaries.
- Add Jira / Linear / Notion integration for turning conversations into work items.
- Add Slack / Teams integration for summaries, mentions, and agent workflows.
- Add project templates and team playbooks.
- Add credential vault / provider management for teams.

## Phase 5 — Advanced intelligence layer
- Add a project knowledge graph connecting code, systems, owners, incidents, and decisions.
- Add impact analysis and change awareness.
- Add explainability and observability for agent outputs, memory sources, and model decisions.
- Add background agents for review, planning, debugging, and release readiness.
- Add a decision log and institutional memory views for teams.

## Phase 6 — Enterprise readiness
- Add SSO / SAML and SCIM provisioning.
- Add audit logs and retention controls.
- Add data residency and private deployment options.
- Add BYO model/provider routing policies.
- Add admin controls for usage, access, and compliance.

## Highest-value SaaS features
1. Organizations and team workspaces
2. Cloud-synced memory
3. GitHub/GitLab integrations
4. Shared threads and async collaboration
5. Background multi-agent execution
6. Project knowledge graph
7. Review and governance workflows
8. Admin analytics and ROI reporting
9. Secure team credential management
10. Enterprise controls

## Desired output from Task Master
When parsing this PRD, prefer a task structure grouped roughly into:
- desktop core / foundation
- memory and knowledge systems
- agent orchestration
- collaboration and cloud sync
- integrations
- analytics and governance
- enterprise

Within each group, prioritize:
1. user-facing value
2. technical dependencies
3. migration path from desktop-first to SaaS
