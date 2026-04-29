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

# Resolve paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = str(_PROJECT_ROOT / "skills")

# Output directory is outside the project tree so that LangGraph Server's
# file watcher (watchfiles) doesn't trigger a reload every time the agent
# writes a generated project file. This prevents the server from restarting
# mid-conversation and killing the agent's run.
_DEFAULT_OUTPUT_DIR = Path.home() / ".deepagent" / "output"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR)))

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek-v4-flash:cloud")
REACT_DEV_MODEL = os.environ.get("REACT_DEV_MODEL", "deepseek-v4-flash:cloud")

REACT_DEV_SYSTEM_PROMPT = """You are an expert React frontend developer. When given a description, you scaffold a Vite+React+TypeScript+Tailwind project and write all components.

Follow the react-scaffolding skill for project setup.
Follow the react-component-patterns skill for UI components.

## CRITICAL: Available Tools

You ONLY have access to these tools:
- `write_file(path, content)` — Create a new file (content must be a string, not a dict)
- `edit_file(path, old_string, new_string)` — Edit an existing file by find-and-replace
- `read_file(path)` — Read file contents
- `ls(path)` — List directory contents
- `glob(pattern)` — Find files by pattern
- `grep(pattern, path)` — Search file contents
- `write_todos(todos)` — Update your todo list

You do NOT have access to `bash`, `execute`, `npm`, `npx`, `mkdir`, or any shell commands.
DO NOT attempt to call `bash` or `execute` — they will fail with an error.
All project setup must be done via `write_file` (creating files) and `edit_file` (modifying files).

## CRITICAL: Output Directory

ALL project files MUST be written inside the `/` virtual root (which maps to the host output directory).
Use paths like `/my-app/package.json`, `/my-app/src/App.tsx`, etc.
NEVER write to absolute host paths like `/tmp/` or `/Users/...` — the backend will sanitize or reject them.
Create a subfolder for each project: `/<project-name>/package.json`, etc.

## CRITICAL: Workflow

1. Use `write_todos` to plan your work
2. Create all project files under `/<project-name>/` using `write_file`
3. If you need to modify a file that already exists, use `edit_file` (NOT `write_file` — it will error)
4. After writing all files, report completion with the file tree and instructions for the user to run `npm install && npm run dev`

DO NOT attempt to run `npm install` or `npm run dev` yourself. You CANNOT execute shell commands.

## CRITICAL: Tool Call Format

When calling `write_file`, the `content` parameter MUST be a plain string, NOT a dict/object.
ALWAYS pass file content as a string: write_file(path='...', content='...')
NEVER pass content as a dict/object. Stringify JSON/YAML content before passing it.

## CRITICAL: File Quality Rules

1. **JSON files must be valid JSON** — No `//` comments in `.json` files (they are invalid JSON)
2. **No unused imports** — TypeScript strict mode with `noUnusedLocals` rejects them, breaking `tsc -b`
3. **No unused destructured variables** — `const { foo, bar } = useHook()` where `bar` is unused will break the build. Only destructure what you use.
4. **No junk files** — Never create `test.txt`, `.gitkeep`, `test-check.txt`, or any scratch/temp files. Only create files that are part of the project.
5. **`moduleResolution: "bundler"`** — Required in BOTH `tsconfig.app.json` AND `tsconfig.node.json`, or `tsc -b` will fail on `vite.config.ts`
6. **Tailwind CSS 4** — Use `@import "tailwindcss"` in `index.css`. No `tailwind.config.js` or `postcss.config.js` needed. Use `@tailwindcss/vite` plugin in `vite.config.ts`.

## Design Principles

- Use Tailwind CSS utility classes
- Mobile-responsive by default
- Realistic mock data (not lorem ipsum)
- Working interactions (button clicks, form inputs, toggles)
- Clean component decomposition
- NEVER leave placeholder content
- Prefer inline SVG for icons (1-3 icons). Use `lucide-react` only for projects needing many icons
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

    Some models pass write_file content as a dict instead of a string.
    Used at both the Pydantic schema level and the backend level so dict
    content is JSON-serialized and non-str primitives are stringified.
    """
    if isinstance(v, dict):
        return json.dumps(v, indent=2)
    if not isinstance(v, str):
        return str(v)
    return v


class RobustFilesystemBackend(FilesystemBackend):
    """FilesystemBackend that sandboxed writes to an output directory.

    Uses virtual_mode=True to contain all writes under root_dir.
    Additionally sanitizes paths: if a model emits an absolute host path
    (e.g. /Users/.../counter-app/src/App.tsx), it's collapsed into a
    virtual path (e.g. /counter-app/src/App.tsx) before resolution.

    Also auto-serializes dict content to JSON strings (defense-in-depth
    for models that pass write_file content as a dict instead of a str).
    """

    # Prefixes that indicate accidental absolute host paths.
    # If a path starts with one of these, strip it to get just the project name onward.
    _HOST_PREFIXES = ("/Users/", "/home/", "/tmp/", "/var/", "/opt/", "/etc/")

    # Known directory names that should be stripped from host paths.
    # These are parent directories of the output dir that models sometimes include.
    _STRIP_DIRS = ("deepagent-1", "output", "development",)

    def __init__(self, root_dir: str | Path, virtual_mode: bool = True) -> None:
        # Ensure output directory exists
        Path(root_dir).mkdir(parents=True, exist_ok=True)
        super().__init__(root_dir=root_dir, virtual_mode=virtual_mode)

    @classmethod
    def _sanitize_path(cls, file_path: str) -> str:
        """Collapse absolute host paths into virtual paths.

        Models sometimes emit paths like /Users/scott/.../counter-app/src/App.tsx
        or /tmp/counter-app/package.json. In virtual_mode, these resolve to
        root_dir/Users/... or root_dir/tmp/... which creates nested junk paths.

        Strategy:
        1. If the path contains our output directory name, strip everything
           before and including it— keep only what comes after output/.
        2. If it starts with a known host prefix but has no output/ segment,
           find the first segment that looks like a project directory.
        3. Otherwise, pass through unchanged (virtual paths like /my-app/...).

        Examples:
          /Users/scott/output/counter-app/src/App.tsx -> /counter-app/src/App.tsx
          /tmp/counter-app/package.json               -> /counter-app/package.json
          /counter-app/src/App.tsx                    -> /counter-app/src/App.tsx (unchanged)
        """
        if not file_path.startswith(cls._HOST_PREFIXES):
            # Already a virtual path or relative path — pass through
            return file_path

        # Strategy 2: if the path contains "output/", strip everything before it
        idx = file_path.find("/output/")
        if idx >= 0:
            return file_path[idx + len("/output/"):]  # e.g. "counter-app/src/App.tsx"
            # Note: result is relative, which virtual_mode resolves under root_dir

        # Strategy 3: skip known parent directory names (deepagent-1, output, development),
        # then find the first remaining project-like segment
        parts = Path(file_path).parts[1:]  # strip leading "/"
        # Filter out known parent dirs
        remaining = [p for p in parts if p not in cls._STRIP_DIRS]
        if remaining:
            # Find first project-like segment (has hyphen or is a known project subdir)
            for i, part in enumerate(remaining):
                if "-" in part or part in ("src", "public", "dist", "build", "node_modules"):
                    return "/" + "/".join(remaining[i:])
            # No project-like segment found; use the first remaining segment as project root
            if len(remaining) >= 2 and Path(file_path).suffix:
                return "/" + "/".join(remaining[-2:])
            return "/" + remaining[0]

        # Fallback: use the last segment(s)
        if parts:
            if Path(file_path).suffix and len(parts) >= 2:
                return "/" + "/".join(parts[-2:])
            return "/" + parts[-1]

        return file_path

    def write(self, file_path: str, content) -> WriteResult:
        content = _coerce_to_str(content)
        file_path = self._sanitize_path(file_path)
        return super().write(file_path, content)

    async def awrite(self, file_path: str, content) -> WriteResult:
        content = _coerce_to_str(content)
        file_path = self._sanitize_path(file_path)
        return await super().awrite(file_path, content)


class _PatchedWriteFileSchema(BaseModel):
    """Pydantic schema for write_file that coerces dict content to JSON strings.

    In deepagents 0.4.x, StructuredTool.from_function() auto-generates the
    args_schema from type annotations. The `content: str` annotation causes
    Pydantic to reject dicts outright with ValidationError. This schema replaces
    the auto-generated one and adds a field_validator to coerce dicts/lists to
    strings before Pydantic's str validation rejects them.
    """

    file_path: Annotated[str, "Absolute path where the file should be created. Use paths like /my-app/package.json — these map to the project output directory."]
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

backend = RobustFilesystemBackend(
    root_dir=str(OUTPUT_DIR),
    virtual_mode=True,
)

agent = create_deep_agent(
    model=_build_model(ORCHESTRATOR_MODEL),
    system_prompt=(
        "You are a frontend development agent. When the user describes a web app, "
        "you use the `task` tool to delegate to the `react-developer` subagent, "
        "which scaffolds and builds a complete React frontend. "
        "The subagent writes all project files but CANNOT execute shell commands — "
        "it cannot run npm install or npm run dev. After the subagent completes, "
        "tell the user to run `cd output/<project-name> && npm install && npm run dev` themselves. "
        "Do NOT spawn additional subagents to 'install dependencies' or 'start the dev server' — "
        "those tasks require shell execution which no subagent can perform. "
        "Present results clearly and help the user iterate on the design."
    ),
    skills=[f"{SKILLS_DIR}/"],
    backend=backend,
    subagents=[
        {
            "name": "react-developer",
            "description": (
                "Generates complete React frontend projects from descriptions. "
                "Writes all project files (Vite+React+TypeScript+Tailwind) using filesystem tools. "
                "CANNOT execute shell commands — no npm install, no npm run dev. "
                "Use this for ANY request to build, create, or design a web app or UI."
            ),
            "system_prompt": REACT_DEV_SYSTEM_PROMPT,
            "model": _build_model(REACT_DEV_MODEL),
            "skills": [f"{SKILLS_DIR}/"],
        },
    ],
)