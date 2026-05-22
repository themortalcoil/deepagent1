"""DeepAgent entry point for LangGraph Server.

Exports `agent` — a CompiledStateGraph that LangGraph Server loads.
"""

import json
import os
from pathlib import Path
from typing import Annotated

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import WriteResult
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain_ollama import ChatOllama
from pydantic import BaseModel, field_validator

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


def _coerce_to_str(v) -> str:
    """Coerce dict/list/primitive values to strings for tool calls.

    GLM models sometimes pass write_file content as a dict instead of a string.
    Used at both the Pydantic schema level and the backend level so dict
    content is JSON-serialized and non-str primitives are stringified.
    """
    if isinstance(v, dict):
        return json.dumps(v, indent=2)
    if not isinstance(v, str):
        return str(v)
    return v


class RobustFilesystemBackend(FilesystemBackend):
    """FilesystemBackend that auto-serializes dict content to JSON strings.

    Some models (e.g., GLM) pass write_file content as a dict instead of a str.
    This subclass coerces any non-string content before delegating to the parent.
    Serves as defense-in-depth for direct backend calls that bypass Pydantic validation.
    """

    def write(self, file_path: str, content) -> WriteResult:
        content = _coerce_to_str(content)
        return super().write(file_path, content)

    async def awrite(self, file_path: str, content) -> WriteResult:
        content = _coerce_to_str(content)
        return await super().awrite(file_path, content)


class _PatchedWriteFileSchema(BaseModel):
    """Pydantic schema for write_file that coerces dict content to JSON strings.

    In deepagents 0.4.x, StructuredTool.from_function() auto-generates the
    args_schema from type annotations. The `content: str` annotation causes
    Pydantic to reject dicts outright with ValidationError. This schema replaces
    the auto-generated one and adds a field_validator to coerce dicts/lists to
    strings before Pydantic's str validation rejects them.
    """

    file_path: Annotated[str, "Absolute path where the file should be created. Must be absolute, not relative."]
    content: Annotated[str, "The text content to write to the file. This parameter is required."]

    model_config = {"extra": "allow"}

    @field_validator("content", mode="before")
    @classmethod
    def _coerce_content_to_str(cls, v):
        return _coerce_to_str(v)


# Monkey-patch FilesystemMiddleware._create_write_file_tool to swap in the
# patched args_schema. This is necessary because create_deep_agent() creates
# FilesystemMiddleware instances internally (in gp_middleware, subagent_middleware,
# and deepagent_middleware) — we can't replace them via the middleware= parameter
# without creating duplicate tools. Patching the method ensures ALL instances
# created by create_deep_agent() use the coercing schema.
_original_create_write_file_tool = FilesystemMiddleware._create_write_file_tool


def _patched_create_write_file_tool(self):
    tool = _original_create_write_file_tool(self)
    tool.args_schema = _PatchedWriteFileSchema
    return tool


FilesystemMiddleware._create_write_file_tool = _patched_create_write_file_tool

backend = RobustFilesystemBackend(root_dir=str(_PROJECT_ROOT))

agent = create_deep_agent(
    model=_build_model(ORCHESTRATOR_MODEL),
    system_prompt=(
        "You are a frontend development agent. When the user describes a web app, "
        "you use the `task` tool to delegate to the `react-developer` subagent, "
        "which scaffolds and builds a complete React frontend. "
        "Present results clearly and help the user iterate on the design."
    ),
    skills=[f"{SKILLS_DIR}/"],
    backend=backend,
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