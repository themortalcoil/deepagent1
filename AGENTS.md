# Agent instructions for deepagent-1

A full-stack Deep Agent system: a LangGraph-backed agent that generates React frontends from natural language, served via LangGraph Server and consumed by a React chat UI.

## Stack

- **Backend**: Python 3.11+, `deepagents>=0.4.8`, `langchain-ollama`, LangGraph Server
- **Chat Frontend**: React 19, TypeScript, Tailwind CSS 4, Vite, `@langchain/react`, `@langchain/langgraph-sdk`
- **Models**: Ollama Cloud (`deepseek-v4-flash:cloud` for both orchestrator and react-developer)
- **Package / env**: [uv](https://docs.astral.sh/uv/)
- **Tasks**: [just](https://github.com/casey/just) — see `justfile`

## Architecture

```
User → React Chat UI (frontend/)
         ↓ SSE (LangGraph Server API)
       DeepAgent (src/agent.py)
         ↓ task tool
       react-developer subagent
         ↓ write_file / execute tools
       Vite+React project (in output/ directory)
         ↓ npm run dev
       Working app on localhost:5173
```

## Output Directory

Generated projects are written to `~/.deepagent/output/` (outside the project tree), sandboxed via `virtual_mode=True` on the FilesystemBackend. The agent uses virtual paths like `/my-app/package.json` which map to `~/.deepagent/output/my-app/package.json`. This prevents writes anywhere else on the filesystem.

**Why outside the project tree?** The LangGraph Server uses `watchfiles` (via uvicorn) to watch for code changes and hot-reload. If `output/` were inside the project directory, every file the agent writes would trigger a server restart, killing the agent's run mid-conversation. Moving the output directory to `~/.deepagent/output/` completely avoids this problem since the watcher only monitors the project directory.

Override the output location with the `OUTPUT_DIR` env var if needed.

## Run the system

### 1. Start LangGraph Server

```bash
just server
# or: uv run langgraph dev
# Serves on http://127.0.0.1:2024
```

### 2. Start the chat frontend

```bash
cd frontend && npm run dev
# Serves on http://localhost:5173
```

### 3. Use it

Open http://localhost:5173, type a description like "Build me a task tracker app", and the agent will scaffold a React frontend. The agent writes all project files but CANNOT execute shell commands — after it finishes, run the generated app manually:

```bash
cd ~/.deepagent/output/<project-name> && npm install && npm run dev
```

### 4. CLI (alternative)

```bash
just run                                    # default prompt
just run-prompt "Build me a weather app"    # custom prompt
```

## Project layout

| Path | Role |
|------|------|
| `src/agent.py` | Agent graph definition (exported for LangGraph Server) |
| `src/__init__.py` | Package init |
| `main.py` | CLI entry point (backward compat) |
| `langgraph.json` | LangGraph Server config |
| `skills/` | Agent skill files loaded by SkillsMiddleware |
| `skills/react-scaffolding/` | Vite+React+Tailwind setup instructions |
| `skills/react-component-patterns/` | UI component patterns |
| `frontend/` | React chat UI (Vite+React+TS+Tailwind) |
| `frontend/src/hooks/useDeepAgent.ts` | Hook wrapping @langchain/react useStream |
| `frontend/src/components/` | ChatMessage, ChatInput, SubagentStatus |
| `frontend/src/App.tsx` | Main chat interface with error boundary |
| `~/.deepagent/output/` | Generated project output directory (sandboxed, outside project tree) |
| `pyproject.toml` | Python project metadata and dependencies |
| `justfile` | Task runner recipes |
| `.env.example` | Environment variable documentation |

## Models

Override models via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_MODEL` | `deepseek-v4-flash:cloud` | Main agent routing/planning |
| `REACT_DEV_MODEL` | `deepseek-v4-flash:cloud` | React code generation subagent |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OUTPUT_DIR` | `~/.deepagent/output` | Generated project output directory |

Available Ollama Cloud models (see `.env.example` for full list):
- **deepseek-v4-flash:cloud** — 284B MoE (13B active), top coding benchmarks, 1M context (recommended)
- **deepseek-v4-pro:cloud** — 158B, frontier reasoning, best quality
- **kimi-k2.6:cloud** — 1T MoE, agentic/swarm, vision
- **glm-5:cloud** / **glm-5.1:cloud** — 756B, agentic engineering
- **qwen3.5:cloud** — 397B, multimodal (vision)
- **qwen3-coder-next:cloud** — 80B, coding-focused
- **nemotron-3-super:cloud** — 120B MoE (12B active), efficient

## Verification

1. `uv run python -c "from src.agent import agent; print('OK')"` — agent imports cleanly
2. `cd frontend && npm run build` — chat UI builds
3. `just server` — LangGraph Server starts on :2024
4. End-to-end: open chat UI, send a prompt, see agent respond

## Known Limitations

- **No shell execution** — The subagent only has filesystem tools (`write_file`, `edit_file`, `read_file`, `ls`, `glob`, `grep`). It CANNOT run `npm install`, `npm run dev`, or any shell commands. The orchestrator should instruct the user to run these manually.
- **Orchestrator over-delegation** — The orchestrator may try to spawn a second subagent to "install dependencies" or "start the dev server" after the react-developer finishes. This wastes time and creates junk files. The orchestrator prompt now explicitly tells it NOT to do this.
- **`write_file` overwrites** — The `write_file` tool rejects existing files. Use `edit_file` (find-and-replace) for modifications.

## Guidelines for code changes

- Agent code lives in `src/agent.py`; skills in `skills/`
- Chat UI lives in `frontend/`
- After Python dependency changes: `uv sync`
- After JS dependency changes: `cd frontend && npm install`
- Do not commit `.env` files — use `.env.example` for documentation
- Frontend uses TypeScript strict mode — run `npm run build` to check types
- Generated projects also use TypeScript strict mode — the skills enforce `moduleResolution: "bundler"` in both tsconfigs