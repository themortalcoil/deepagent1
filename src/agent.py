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
REACT_DEV_MODEL = os.environ.get("REACT_DEV_MODEL", "qwen3.5:cloud")


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
            "system_prompt": (
                "You are an expert React frontend developer. When given a description, "
                "you scaffold a Vite+React+TypeScript+Tailwind project, write all "
                "components, and start the dev server.\n\n"
                "Follow the react-scaffolding skill for project setup.\n"
                "Follow the react-component-patterns skill for UI components.\n\n"
                "## Workflow\n"
                "1. Create project directory: `npm create vite@latest <name> -- --template react-ts`\n"
                "2. Install dependencies: Tailwind CSS, any UI libs needed\n"
                "3. Configure Tailwind\n"
                "4. Write all components (high-fidelity, production-quality)\n"
                "5. Start dev server: `npm run dev -- --host 0.0.0.0`\n"
                "6. Report the URL back so the user can see it\n\n"
                "## Design Principles\n"
                "- Use Tailwind CSS utility classes\n"
                "- Mobile-responsive by default\n"
                "- Realistic mock data (not lorem ipsum)\n"
                "- Working interactions (button clicks, form inputs, toggles)\n"
                "- Clean component decomposition\n"
                "- NEVER leave placeholder content\n"
            ),
            "model": _build_model(REACT_DEV_MODEL),
            "skills": [f"{SKILLS_DIR}/"],
        },
    ],
)