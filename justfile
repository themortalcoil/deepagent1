# Deep agent runner (Ollama + LangGraph). Requires https://github.com/casey/just and https://docs.astral.sh/uv/
#
# Environment (optional):
#   OLLAMA_BASE_URL   — e.g. http://host:11434 (default: http://localhost:11434)
#   ORCHESTRATOR_MODEL — orchestrator model (default: deepseek-v4-flash:cloud)
#   REACT_DEV_MODEL   — react-developer subagent model (default: deepseek-v4-flash:cloud)
#   DEEPAGENT_PROMPT  — user message (default: build a todo app)
#
# Ollama Cloud models available (`:cloud` tags) — see AGENTS.md for sizes/use-cases:
#   deepseek-v4-flash:cloud  — top coding benchmarks, 1M context (default)
#   deepseek-v4-pro:cloud    — frontier reasoning, best quality
#   kimi-k2.6:cloud          — agentic/swarm, vision
#   glm-5:cloud / glm-5.1:cloud — agentic engineering
#   qwen3.5:cloud            — multimodal (vision)
#   qwen3-coder-next:cloud   — coding-focused
#   nemotron-3-super:cloud   — efficient MoE
#
# Quick start:
#   just sync        — install deps
#   just server      — start LangGraph Server on :2024
#   just run         — single CLI invocation

default: run

# Install / refresh dependencies
sync:
    uv sync

# Run the agent once via CLI
run:
    uv run python main.py

# Run with custom prompt
run-prompt prompt:
    DEEPAGENT_PROMPT={{prompt}} uv run python main.py

# Start LangGraph Server (in-memory, dev mode) on http://127.0.0.1:2024
server:
    uv run langgraph dev

# Start LangGraph Server on a specific port
server-port port:
    uv run langgraph dev --port {{port}}

# --- Ollama Cloud model overrides ---

# Run with custom models (e.g. just run-models nemotron-3-super:cloud glm-5.1:cloud)
run-models orchestrator dev:
    ORCHESTRATOR_MODEL={{orchestrator}} REACT_DEV_MODEL={{dev}} uv run python main.py

# Convenience: nemotron orchestrator + glm-5.1 dev
run-nemotron-glm:
    ORCHESTRATOR_MODEL=nemotron-3-super:cloud REACT_DEV_MODEL=glm-5.1:cloud uv run python main.py

# --- Tests ---

# Run unit tests
test:
    uv run pytest tests/

# --- Frontend commands ---

# Install frontend dependencies
fe-install:
    cd frontend && npm install

# Start frontend dev server
fe-dev:
    cd frontend && npm run dev

# Build frontend for production
fe-build:
    cd frontend && npm run build

# Preview production build
fe-preview:
    cd frontend && npm run preview

# --- Full stack ---

# Start both LangGraph Server and frontend (requires two terminals or tmux)
dev:
    @echo "In terminal 1: just server"
    @echo "In terminal 2: just fe-dev"
    @echo "Chat UI: http://localhost:5173"
    @echo "LangGraph API: http://127.0.0.1:2024"