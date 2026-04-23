# Deep agent runner (Ollama + LangGraph). Requires https://github.com/casey/just and https://docs.astral.sh/uv/
#
# Environment (optional):
#   OLLAMA_MODEL      — default qwen3:8b (see `run`); cloud recipes set this for you
#   OLLAMA_BASE_URL   — e.g. http://host:11434
#   DEEPAGENT_PROMPT  — user message (default: short LangGraph question)
#
# Ollama Cloud (`:cloud` tags — remote inference via Ollama Cloud; account / plan required):
#   nemotron-3-super:cloud  — primary pick for agentic / reasoning tests
#   minimax-m2.7:cloud      — alternate (newer MiniMax cloud tier)
#   qwen3.5:cloud
#   minimax-m2.5:cloud
#   glm-5:cloud
# Override model ad hoc: `just run-cloud minimax-m2.7:cloud` (quote if the shell splits on `:`)

default: run

# Install / refresh dependencies from pyproject.toml
sync:
    uv sync

# Run the agent once (uv ensures the project env is used)
run:
    uv run python main.py

# Run with any Ollama model name (e.g. cloud or local). Example: `just run-cloud nemotron-3-super:cloud`
run-cloud model:
    OLLAMA_MODEL={{model}} uv run python main.py

# --- Ollama Cloud convenience targets ---

run-cloud-nemotron:
    OLLAMA_MODEL=nemotron-3-super:cloud uv run python main.py

run-cloud-minimax-m27:
    OLLAMA_MODEL=minimax-m2.7:cloud uv run python main.py

run-cloud-qwen35:
    OLLAMA_MODEL=qwen3.5:cloud uv run python main.py

run-cloud-minimax-m25:
    OLLAMA_MODEL=minimax-m2.5:cloud uv run python main.py

run-cloud-glm5:
    OLLAMA_MODEL=glm-5:cloud uv run python main.py
