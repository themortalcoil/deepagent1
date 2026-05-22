# DeepAgent 1

A full-stack Deep Agent system: a LangGraph-backed agent that generates React frontends from natural language, served via LangGraph Server and consumed by a React chat UI.

## Quick Start

```bash
# 1. Install dependencies
just sync
cd frontend && npm install

# 2. Start the backend (LangGraph Server on :2024)
just server

# 3. Start the frontend (Vite dev server on :5173)
just fe-dev
```

Open http://localhost:5173 and type a description like "Build me a task tracker app".

## CLI Usage

```bash
just run                                    # default prompt
just run-prompt "Build me a weather app"    # custom prompt
```

## Models

Override models via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_MODEL` | `glm-5:cloud` | Main agent routing/planning |
| `REACT_DEV_MODEL` | `glm-5.1:cloud` | React code generation subagent |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

Available Ollama Cloud models: `glm-5:cloud`, `glm-5.1:cloud`, `nemotron-3-super:cloud`, `qwen3.5:cloud`, `minimax-m2.7:cloud`, `minimax-m2.5:cloud`

## Architecture

```
User → React Chat UI (frontend/)
         ↓ SSE (LangGraph Server API)
       DeepAgent (src/agent.py)
         ↓ task tool
       react-developer subagent
         ↓ write_file / execute tools
       Vite+React project (generated, on disk)
         ↓ npm run dev
       Working app on localhost:5173
```

## Tech Stack

- **Backend**: Python 3.11+, deepagents, LangGraph Server, langchain-ollama
- **Frontend**: React 19, TypeScript, Tailwind CSS 4, Vite, @langchain/react
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (Python), npm (JS)
- **Task Runner**: [just](https://github.com/casey/just)

## Project Structure

| Path | Role |
|------|------|
| `src/agent.py` | Agent graph definition |
| `skills/` | Agent skill files (react-scaffolding, component-patterns) |
| `frontend/` | React chat UI |
| `langgraph.json` | LangGraph Server config |
| `justfile` | Task runner recipes |
| `pyproject.toml` | Python project metadata |

## See Also

- [AGENTS.md](AGENTS.md) — detailed agent instructions and verification steps