"""CLI entry point for the Deep Agent.

For LangGraph Server usage, see `src/agent.py` (exports `agent`).
This file is kept for `just run` / `uv run python main.py` convenience.
"""

import os

from src.agent import agent


def main() -> None:
    """Run a single agent invocation from the CLI."""
    prompt = os.environ.get(
        "DEEPAGENT_PROMPT",
        "Build me a simple todo list app with React.",
    )
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()