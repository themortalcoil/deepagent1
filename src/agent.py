"""DeepAgent entry point for LangGraph Server.

Exports `agent` — a CompiledStateGraph that LangGraph Server loads.
"""

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_ollama import ChatOllama

from src.middleware import WriteFileSanitizer

# Resolve paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = str(_PROJECT_ROOT / "skills")

# Output directory is outside the project tree so that LangGraph Server's
# file watcher (watchfiles) doesn't trigger a reload every time the agent
# writes a generated project file. This prevents the server from restarting
# mid-conversation and killing the agent's run.
_DEFAULT_OUTPUT_DIR = Path.home() / ".deepagent" / "output"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR)))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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


backend = FilesystemBackend(root_dir=str(OUTPUT_DIR), virtual_mode=True)

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
    middleware=[WriteFileSanitizer()],
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
            "middleware": [WriteFileSanitizer()],
        },
    ],
)
