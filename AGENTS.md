# Agent instructions for deepagent-1

This repository is a minimal Python example of a [Deep Agents](https://github.com/langchain-ai/deepagents) app backed by LangGraph, using [langchain-ollama](https://python.langchain.com/docs/integrations/chat/ollama/) to talk to a local or remote Ollama server.

For Cursor IDE–specific notes (rules, hooks, MCP), see the [Cursor](#cursor) section below.

## Stack

- **Python** 3.11+ (`requires-python` in `pyproject.toml`)
- **Dependencies**: `deepagents`, `langchain-ollama` (see `pyproject.toml`)
- **Package / env**: [uv](https://docs.astral.sh/uv/)
- **Tasks**: [just](https://github.com/casey/just) — see `justfile`

## Run the app

1. Install [Ollama](https://ollama.com/) and pull a model that supports tool use (the default in code is `qwen3:8b`; override with `OLLAMA_MODEL`).
2. From the repo root:
   - `just sync` — install dependencies
   - `just` or `just run` — run `main.py` via `uv run`

Optional environment variables (documented in `main()` in `main.py`):

| Variable | Purpose |
|----------|---------|
| `OLLAMA_MODEL` | Model name (default `qwen3:8b`) |
| `OLLAMA_BASE_URL` | Non-default Ollama URL, e.g. `http://host:11434` |
| `DEEPAGENT_PROMPT` | User message; default is a short LangGraph question |

Example:

```bash
DEEPAGENT_PROMPT="What is 2+2?" just run
```

## Project layout

| Path | Role |
|------|------|
| `main.py` | Entry point: builds `ChatOllama`, `create_deep_agent`, single `invoke` |
| `pyproject.toml` | Project metadata and dependencies |
| `justfile` | `sync`, `run` (default) |
| `.gitignore` | Ignores `.venv/`, `.env*`, caches, build artifacts |

There is no test suite or CI configuration in-repo yet; if you add one, document the canonical command here.

## Cursor

This file (`AGENTS.md`) is project-level context for [Cursor](https://cursor.com/) agents alongside user rules. Prefer it for repo-specific facts (stack, commands, layout) so chat stays aligned with what is actually in the tree.

- **Rules** — Persistent, scoped guidance lives in `.cursor/rules/` as `.mdc` files (YAML frontmatter: `description`, optional `globs`, `alwaysApply`). See [Cursor Rules](https://cursor.com/docs/rules). Use rules for file-type or path-specific conventions; use this `AGENTS.md` for global project orientation and runbooks.
- **Hooks** — Optional automation around agent lifecycle lives in `.cursor/hooks.json` and hook scripts if you add them; nothing is configured in-repo by default.
- **MCP** — Model Context Protocol servers are user/workspace settings in Cursor. This demo does not require MCP; enable servers only when a task needs external tools (docs APIs, issue trackers, etc.).
- **Terminal** — Prefer `just run` / `just sync` from the repo root so the same entry points humans use match agent verification steps above.

## Guidelines for code changes

- Prefer small, focused edits; keep `main.py` readable as a demo unless the user asks for a larger structure (e.g. package layout, CLI).
- Match existing style: type hints where used, env-based configuration, docstring on `main()` for env contract.
- Do not commit secrets; use `.env` locally if needed (gitignored). Prefer env vars already supported by `main.py` when extending configuration.
- After dependency changes, ensure `pyproject.toml` stays consistent and mention `just sync` / `uv sync` in any setup notes you add.

## Verification

Before claiming the app runs: execute `just run` (or `uv run python main.py`) and confirm it completes without import errors; Ollama must be reachable for a successful end-to-end run.
