"""DeepAgent entry point for LangGraph Server.

Exports `agent` — a CompiledStateGraph that LangGraph Server loads.
"""

import os
from pathlib import Path

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama

# Resolve skills directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = str(_PROJECT_ROOT / "skills")

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "glm-5:cloud")
REACT_DEV_MODEL = os.environ.get("REACT_DEV_MODEL", "glm-5.1:cloud")

REACT_DEV_SYSTEM_PROMPT = """You are an expert React frontend developer. When given a description, you scaffold a Vite+React+TypeScript+Tailwind project, write all components, and start the dev server.

Follow the react-scaffolding skill for project setup.
Follow the react-component-patterns skill for UI components.

## Workflow
1. Create project directory: `npm create vite@latest <name> -- --template react-ts`
2. Install dependencies: Tailwind CSS, any UI libs needed
3. Configure Tailwind
4. Write all components (high-fidelity, production-quality)
5. Start dev server: `npm run dev -- --host 0.0.0.0`
6. Report the URL back so the user can see it

## CRITICAL: Tool Call Format
When calling write_file, the `content` parameter MUST be a plain string, NOT a dict/object.
ALWAYS pass file content as a string: write_file(path='...', content='...')
NEVER pass content as a dict/object. Stringify JSON/YAML content before passing it.

## Design Principles
- Use Tailwind CSS utility classes
- Mobile-responsive by default
- Realistic mock data (not lorem ipsum)
- Working interactions (button clicks, form inputs, toggles)
- Clean component decomposition
- NEVER leave placeholder content
"""

def _build_model(model_name: str) -> ChatOllama:
    """Build a ChatOllama model instance."""
    kwargs: dict = {"model": model_name}
    base_url = os.environ.get("OLLAMA_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)


agent = create_deep_agent(
    model=_build_model(ORCHESTRATOR_MODEL),
    system_prompt=(
        "You are a frontend development agent. When the user describes a web app, "
        "you use the `task` tool to delegate to the `react-developer` subagent, "
        "which scaffolds and builds a complete React frontend. "
        "Present results clearly and help the user iterate on the design."
    ),
    skills=[f"{SKILLS_DIR}/"],
    subagents=[
        {
            "name": "react-developer",
            "description": (
                "Generates complete React frontends from descriptions. "
                "Scaffolds Vite+React+Tailwind projects, writes components, "
                "installs dependencies, and starts dev servers. "
                "Use this for ANY request to build, create, or design a web app or UI."
            ),
            "system_prompt": REACT_DEV_SYSTEM_PROMPT,
            "model": _build_model(REACT_DEV_MODEL),
            "skills": [f"{SKILLS_DIR}/"],
        },
    ],
)