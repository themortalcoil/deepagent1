# Deep agent runner (Ollama + LangGraph). Requires https://github.com/casey/just and https://docs.astral.sh/uv/
#
# Environment (optional):
#   OLLAMA_BASE_URL   — e.g. http://host:11434 (default: http://localhost:11434)
#   ORCHESTRATOR_MODEL — orchestrator model (default: glm-5:cloud)
#   REACT_DEV_MODEL   — react-developer subagent model (default: qwen3.5:cloud)
#   DEEPAGENT_PROMPT  — user message (default: build a todo app)
#
# Ollama Cloud models available (`:cloud` tags):
#   glm-5:cloud             — strong orchestrator
#   nemotron-3-super:cloud  — alternate orchestrator
#   qwen3.5:cloud           — good code model for subagent
#   minimax-m2.7:cloud     — alternate code model
#   minimax-m2.5:cloud
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

# Run with custom models (e.g. just run-models nematron-3-super:cloud qwen3.5:cloud)
run-models orchestrator dev:
    ORCHESTRATOR_MODEL={{orchestrator}} REACT_DEV_MODEL={{dev}} uv run python main.py

# Convenience: nematron orchestrator + qwen3.5 dev
run-nematron-qwen:
    ORCHESTRATOR_MODEL=nematron-3-super:cloud REACT_DEV_MODEL=qwen3.5:cloud uv run python main.py