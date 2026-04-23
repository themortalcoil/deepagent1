# Deep agent runner (Ollama + LangGraph). Requires https://github.com/casey/just and https://docs.astral.sh/uv/
#
# Environment (optional):
#   OLLAMA_MODEL      — default qwen3:8b
#   OLLAMA_BASE_URL   — e.g. http://host:11434
#   DEEPAGENT_PROMPT  — user message (default: short LangGraph question)

default: run

# Install / refresh dependencies from pyproject.toml
sync:
    uv sync

# Run the agent once (uv ensures the project env is used)
run:
    uv run python main.py
