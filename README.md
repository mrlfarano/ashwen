# Ashwen

Ashwen is becoming a cross-platform desktop app for AI-assisted software development.

## Current architecture
- **Electron** desktop shell
- **Svelte** renderer in `frontend/`
- **FastAPI** local backend in `backend/`
- **SQLite** + encrypted credentials stored in the app data directory
- **GitHub Releases** + `electron-updater` for in-app updates

## Local development

### 1. Install dependencies
```bash
npm install
npm --prefix frontend install
pip install -r backend/requirements.txt
```

### 2. Run the desktop app in development
```bash
npm run dev
```

That starts:
- FastAPI backend on `127.0.0.1:8000`
- Svelte dev server on `http://localhost:5173`
- Electron pointed at the dev server

## Build desktop distributions

### Build the frontend
```bash
npm run build:frontend
```

### Build the backend executable
```bash
pip install pyinstaller
npm run build:backend
```

### Package the desktop app
```bash
npm run build:desktop
```

Or run the full pipeline:
```bash
npm run dist
```

## Release flow
Push a tag like:
```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will:
- build Windows and macOS apps
- publish artifacts to GitHub Releases
- make them available to the in-app updater

## Near-term roadmap
- harden Electron startup and packaging
- add first-run onboarding
- add signed Windows/macOS releases
- expand settings, provider management, and local model setup
- improve memory, agent orchestration, and review workflows
- add cloud sync, team workspaces, and collaboration
- integrate with GitHub/GitLab and team tools over time

## Product direction
Ashwen is evolving from a desktop AI-assisted development workspace into a collaborative SaaS for software teams.

Key future areas include:
- shared team workspaces
- cloud-synced memory and decision logs
- GitHub/GitLab integration
- shared threads and async collaboration
- background multi-agent execution
- project knowledge graph and impact analysis
- enterprise-grade admin, security, and compliance controls

See `docs/desktop-architecture.md` for the expanded product and architecture roadmap.
