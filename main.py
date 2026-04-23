import os

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama


def main() -> None:
    """Minimal Deep Agent (LangGraph-backed) using a local or remote Ollama model.

    Env:
      OLLAMA_MODEL — model name (default: qwen3:8b). Use a tag that supports tool calling.
      OLLAMA_BASE_URL — optional; e.g. http://host:11434 for non-default Ollama.
      DEEPAGENT_PROMPT — optional user message (default: short LangGraph question).
    """
    model_name = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    base_url = os.environ.get("OLLAMA_BASE_URL")
    llm_kwargs: dict = {"model": model_name}
    if base_url:
        llm_kwargs["base_url"] = base_url
    model = ChatOllama(**llm_kwargs)

    agent = create_deep_agent(
        model=model,
        system_prompt="You are a helpful assistant. Answer clearly and use tools when they help.",
    )

    prompt = os.environ.get(
        "DEEPAGENT_PROMPT",
        "What is LangGraph in one sentence?",
    )
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
