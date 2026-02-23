# Session Viewer

A web UI for browsing your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [Codex CLI](https://github.com/openai/codex) session histories. Parses the JSONL session files from both tools and presents them in a searchable, filterable interface with full message rendering — including thinking blocks, tool calls, and tool results.

## Features

- Browse and search sessions from both Claude Code and Codex CLI
- Filter by source (Claude/Codex), project, and date
- Full conversation rendering with structured content blocks:
  - Markdown-rendered text
  - Collapsible thinking/reasoning blocks
  - Collapsible tool calls with inputs and outputs
- View project documentation (.md files) inline, including from subdirectories
- Session artifacts (TODO.md, plans, debug logs)
- Token usage tracking per message
- Dark/light mode

## Quick Start (Docker)

```bash
cp env.example .env
# Edit .env — set PROJECT_DIRS to your code directories
./start.sh
```

The app will be available at **http://localhost:3000**.

To stop: `docker compose down`

## Configuration

Copy `env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_DIR` | `~/.claude` | Path to Claude Code sessions directory |
| `CODEX_DIR` | `~/.codex` | Path to Codex CLI sessions directory |
| `PROJECT_DIRS` | *(empty)* | Comma-separated project directories (mounted read-only for viewing `.md` files) |
| `PORT` | `3000` | Port to expose the web UI on |
| `LOG_LEVEL` | `INFO` | Backend log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

`PROJECT_DIRS` lets the viewer display `.md` files (README, CLAUDE.md, TODO.md, etc.) from your project folders, including files in subdirectories. Each file shows its relative path (e.g. `./`, `./docs/`) for easy identification. Dependency and build directories (e.g. `node_modules`, `.venv`, `vendor`, `dist`, `build`) and licence files are automatically excluded. Without it, session browsing still works but the project documentation panel will be empty.

## Running Without Docker

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend auto-detects `~/.claude` and `~/.codex` when running locally. Project `.md` files work automatically since the backend has direct filesystem access.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server runs at `http://localhost:5173` and proxies `/api` to `http://localhost:8000`.

## Architecture

```
┌─────────────┐       ┌──────────────┐
│   Frontend   │──────▶│   Backend    │
│  SvelteKit   │  /api │   FastAPI    │
│  (nginx:80)  │       │  (uvicorn)   │
└─────────────┘       └──────┬───────┘
                              │
                       ┌──────┴───────┐
                       │    SQLite     │
                       │  data/       │
                       │  sessions.db │
                       └──────────────┘
                              ▲
                ┌─────────────┼─────────────┐
                │             │             │
          ~/.claude     ~/.codex     PROJECT_DIRS
          (JSONL)       (JSONL)      (.md files)
```

- **Backend** (Python/FastAPI) — parses JSONL session files, indexes into SQLite, serves REST API
- **Frontend** (SvelteKit/Svelte 5) — static SPA served by nginx, proxies `/api` to the backend
- **Database** — SQLite, auto-created and indexed on first startup

## Data Sources

| Source | Location | Format |
|--------|----------|--------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | One JSONL per session |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` | One JSONL per session |

All session data is mounted **read-only**.

## Re-indexing

The database is built on first startup. To force a full re-index:

```bash
rm data/sessions.db
docker compose restart backend
```

Or via the API:

```bash
curl -X POST http://localhost:3000/api/index/refresh?force=true
```
