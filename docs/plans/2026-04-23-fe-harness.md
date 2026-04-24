# DeepAgent Frontend Harness — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a full-stack system where a DeepAgent (via LangGraph Server) takes a natural-language prompt and produces a working, high-fidelity React frontend, observable through a React chat UI.

**Architecture:** A DeepAgent with a "react-developer" subagent is served via LangGraph Server. The subagent uses FilesystemBackend to write real files and SandboxBackend to run shell commands (npm, vite). A separate React chat app uses `@langchain/react` `useStream` hook to stream conversation, tool calls, and subagent activity from the agent. The agent scaffolds a Vite+React+Tailwind project, writes components, and the user can see the result running on a dev server.

**Tech Stack:**
- Backend: Python 3.11+, deepagents 0.4.8, langchain-ollama, langgraph-cli, Ollama Cloud models
- Agent Server: LangGraph Server (`langgraph dev`)
- Chat Frontend: React 19, Vite, TypeScript, Tailwind CSS 4, @langchain/react, @langchain/langgraph-sdk
- Generated Apps: Vite + React + Tailwind (scaffolding by the agent)
- Models: `glm-5:cloud` (orchestrator), `qwen3.5:cloud` (react-developer subagent) — Ollama Cloud

---

## Phase 0: Project Restructure

### Task 1: Create `src/` package layout for the agent

**Objective:** Move agent code from flat `main.py` into a proper Python package so LangGraph Server can import it.

**Files:**
- Create: `src/__init__.py`
- Create: `src/agent.py`
- Modify: `pyproject.toml` (add `[tool.setuptools.packages]`)

**Step 1: Create the package directory**

```bash
mkdir -p ~/development/deepagent-1/src
```

**Step 2: Create `src/__init__.py`**

```python
"""deepagent-1 agent package."""
```

**Step 3: Create `src/agent.py`**

```python
"""DeepAgent entry point for LangGraph Server.

Exports `agent` — a CompiledStateGraph that LangGraph Server loads.
"""

import os

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama

# --- Model configuration ---
# Orchestrator model (handles routing, planning, user interaction)
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "glm-5:cloud")
# React-developer subagent model (writes code, runs shell commands)
REACT_DEV_MODEL = os.environ.get("REACT_DEV_MODEL", "qwen3.5:cloud")


def _build_model(model_name: str) -> ChatOllama:
    """Build a ChatOllama model instance."""
    kwargs: dict = {"model": model_name}
    base_url = os.environ.get("OLLAMA_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)


# Build the compiled graph at module level so `langgraph dev` can import it.
agent = create_deep_agent(
    model=_build_model(ORCHESTRATOR_MODEL),
    system_prompt=(
        "You are a frontend development agent. When the user describes a web app, "
        "you use the `task` tool to delegate to the `react-developer` subagent, "
        "which scaffolds and builds a complete React frontend. "
        "Present results clearly and help the user iterate on the design."
    ),
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
                "## Workflow\n"
                "1. Create project directory: `npm create vite@latest <name> -- --template react-ts`\n"
                "2. Install dependencies: Tailwind CSS, any UI libs needed\n"
                "3. Configure Tailwind\n"
                "4. Write all components (high-fidelity, production-quality)\n"
                "5. Start dev server: `npm run dev -- --host 0.0.0.0`\n"
                "6. Report the URL back so the user can see it\n\n"
                "## Design Principles\n"
                "- Use Tailwind CSS utility classes; prefer shadcn/ui patterns\n"
                "- Mobile-responsive by default\n"
                "- Realistic mock data (not lorem ipsum)\n"
                "- Working interactions (button clicks, form inputs, toggles)\n"
                "- Clean component decomposition\n"
                "- NEVER leave placeholder content — always use realistic data\n"
            ),
            "model": _build_model(REACT_DEV_MODEL),
        },
    ],
)
```

**Step 4: Update `pyproject.toml` to include the package**

Add after the `[project]` section:

```toml
[tool.setuptools.packages.find]
include = ["src*"]
```

**Step 5: Sync dependencies and verify import works**

```bash
cd ~/development/deepagent-1 && uv sync
uv run python -c "from src.agent import agent; print(type(agent).__name__)"
```

Expected: `CompiledStateGraph` (or similar, no ImportError)

**Step 6: Commit**

```bash
git add src/ pyproject.toml
git commit -m "feat: add src/ package with agent graph for LangGraph Server"
```

---

### Task 2: Keep `main.py` as a CLI entry point (backward compat)

**Objective:** `main.py` still works for `just run` ad-hoc usage, but now imports from `src.agent`.

**Files:**
- Modify: `main.py`

**Step 1: Rewrite `main.py`**

```python
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
```

**Step 2: Verify with `just run` (may fail on Ollama connection if no server — that's OK)**

```bash
cd ~/development/deepagent-1 && uv run python -c "from main import main; print('import OK')"
```

Expected: `import OK`

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: main.py now imports from src.agent package"
```

---

### Task 3: Install `langgraph-cli[inmem]` and create `langgraph.json`

**Objective:** Set up LangGraph Server so the agent is accessible via REST API.

**Files:**
- Create: `langgraph.json`
- Modify: `pyproject.toml` (add langgraph-cli dependency)

**Step 1: Add langgraph-cli to dev dependencies**

```bash
cd ~/development/deepagent-1 && uv add --dev "langgraph-cli[inmem]"
```

**Step 2: Create `langgraph.json`**

```json
{
  "dependencies": ["."],
  "graphs": {
    "deepagent": "./src/agent.py:agent"
  },
  "env": "./.env"
}
```

**Step 3: Verify server starts (then Ctrl+C to stop)**

```bash
cd ~/development/deepagent-1 && uv run langgraph dev
```

Expected: Server starts on `http://127.0.0.1:2024`, shows "deepagent" graph loaded.

**Step 4: Commit**

```bash
git add langgraph.json pyproject.toml uv.lock
git commit -m "feat: add langgraph.json and langgraph-cli for dev server"
```

---

### Task 4: Add `.env` file with Ollama Cloud config

**Objective:** Configure environment variables for the dev server and models.

**Files:**
- Create: `.env.example`
- Modify: `.gitignore` (ensure `.env` is ignored)

**Step 1: Create `.env.example`**

```env
# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434

# Model selection (Ollama Cloud models)
ORCHESTRATOR_MODEL=glm-5:cloud
REACT_DEV_MODEL=qwen3.5:cloud

# Alternative models:
# ORCHESTRATOR_MODEL=nemotron-3-super:cloud
# REACT_DEV_MODEL=minimax-m2.7:cloud
```

**Step 2: Verify `.gitignore` includes `.env`**

```bash
grep -q "\.env" ~/development/deepagent-1/.gitignore && echo "OK" || echo ".env missing from gitignore"
```

If missing, add `.env` to `.gitignore`.

**Step 3: Copy `.env.example` to `.env` for local dev**

```bash
cp ~/development/deepagent-1/.env.example ~/development/deepagent-1/.env
```

**Step 4: Commit**

```bash
git add .env.example .gitignore
git commit -m "feat: add .env.example with Ollama Cloud model config"
```

---

### Task 5: Update `justfile` with server and new model commands

**Objective:** Add justfile recipes for `langgraph dev` and the new model names.

**Files:**
- Modify: `justfile`

**Step 1: Replace justfile contents**

```just
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

# Run with custom models (e.g. just run-models nemotron-3-super:cloud qwen3.5:cloud)
run-models orchestrator dev:
    ORCHESTRATOR_MODEL={{orchestrator}} REACT_DEV_MODEL={{dev}} uv run python main.py

# Convenience: nematron orchestrator + qwen3.5 dev
run-nematron-qwen:
    ORCHESTRATOR_MODEL=nemotron-3-super:cloud REACT_DEV_MODEL=qwen3.5:cloud uv run python main.py
```

**Step 2: Verify justfile parses**

```bash
cd ~/development/deepagent-1 && just --list
```

Expected: List of all recipes shown without errors.

**Step 3: Commit**

```bash
git add justfile
git commit -m "feat: update justfile with server recipes and Ollama Cloud models"
```

---

## Phase 1: React Agent Skills

### Task 6: Create the `react-scaffolding` skill for the agent

**Objective:** Create a skill file that teaches the react-developer subagent how to scaffold a Vite+React+Tailwind project. This skill is loaded by `SkillsMiddleware` into the subagent's system prompt.

**Files:**
- Create: `skills/react-scaffolding/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p ~/development/deepagent-1/skills/react-scaffolding
```

**Step 2: Create `skills/react-scaffolding/SKILL.md`**

```markdown
---
name: react-scaffolding
description: Scaffold a complete Vite + React + TypeScript + Tailwind CSS 4 project with consistent patterns.
version: 1.0.0
---

# React Scaffolding

## Creating a New Project

Always scaffold into a subdirectory under `/workspace/` (or the current working directory).

### Step 1: Create Vite project

```bash
npm create vite@latest PROJECT_NAME -- --template react-ts
cd PROJECT_NAME
```

### Step 2: Install core dependencies

```bash
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### Step 3: Configure Tailwind CSS 4

In `vite.config.ts`, add the Tailwind plugin:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['all'],
  },
})
```

In `src/index.css`, replace all content with:

```css
@import "tailwindcss";
```

### Step 4: Clean up template files

Remove:
- `src/App.css`
- `src/assets/` (if empty)
- `public/vite.svg`

Update `src/App.tsx` to a minimal shell:

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Components go here */}
    </div>
  )
}
```

### Step 5: Common additional dependencies

Install as needed based on the app requirements:

| Purpose | Package | Install |
|---------|---------|---------|
| Icons | `lucide-react` | `npm install lucide-react` |
| Routing | `react-router-dom` | `npm install react-router-dom` |
| State | `zustand` | `npm install zustand` |
| Forms | `react-hook-form` | `npm install react-hook-form` |
| Date | `date-fns` | `npm install date-fns` |
| Charts | `recharts` | `npm install recharts` |
| Animation | `framer-motion` | `npm install framer-motion` |

### Step 6: Start dev server

```bash
npm run dev -- --host 0.0.0.0
```

This starts on `http://localhost:5173` (or next available port). The `--host 0.0.0.0` makes it accessible on the network.

## Project Structure Convention

```
project-name/
  src/
    components/     # Reusable UI components
      ui/           # Base primitives (Button, Card, Input, etc.)
    hooks/          # Custom React hooks
    lib/            # Utility functions
    data/           # Mock data files
    App.tsx          # Root component
    main.tsx        # Entry point
    index.css       # Tailwind imports
  index.html
  vite.config.ts
  tailwind.config.ts  # Only needed for Tailwind v3; v4 uses CSS config
  package.json
```
```

**Step 3: Commit**

```bash
git add skills/
git commit -m "feat: add react-scaffolding skill for DeepAgent subagent"
```

---

### Task 7: Create the `react-component-patterns` skill

**Objective:** Give the agent production-quality React component patterns to copy, so it generates consistent, beautiful UIs.

**Files:**
- Create: `skills/react-component-patterns/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p ~/development/deepagent-1/skills/react-component-patterns
```

**Step 2: Create `skills/react-component-patterns/SKILL.md`**

```markdown
---
name: react-component-patterns
description: Production-quality React component patterns using Tailwind CSS. Follow these patterns when generating UI components.
version: 1.0.0
---

# React Component Patterns

## Design Principles

1. **Tailwind-first** — Use utility classes, not custom CSS
2. **Composition over configuration** — Small components, composed in pages
3. **TypeScript strict** — Props interfaces for every component
4. **Realistic data** — Never use "Lorem ipsum" or placeholder text
5. **Working interactions** — Every button, toggle, and form must do something (even if mocked with `useState`)
6. **Mobile-first** — Start with mobile layout, add `md:` and `lg:` breakpoints
7. **Accessible** — Use semantic HTML, `aria-*` where needed

## Base Components

### Button

```tsx
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

const variants = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm',
  secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
  ghost: 'text-gray-600 hover:bg-gray-100',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
```

### Card

```tsx
interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: CardProps) {
  return <div className={`p-6 pb-0 ${className}`}>{children}</div>
}

export function CardContent({ children, className = '' }: CardProps) {
  return <div className={`p-6 pt-0 ${className}`}>{children}</div>
}
```

### Input

```tsx
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function Input({ label, error, className = '', id, ...props }: InputProps) {
  return (
    <div className="space-y-1">
      {label && <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>}
      <input
        id={id}
        className={`block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500 ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''} ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
```

### Badge

```tsx
interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  children: React.ReactNode
}

const badgeVariants = {
  default: 'bg-gray-100 text-gray-700',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  error: 'bg-red-50 text-red-700',
  info: 'bg-blue-50 text-blue-700',
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeVariants[variant]}`}>
      {children}
    </span>
  )
}
```

## Layout Patterns

### App Shell (Sidebar + Main)

```tsx
export function AppShell({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-gray-200 md:bg-white">
        {sidebar}
      </aside>
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
```

### Page Header

```tsx
interface PageHeaderProps {
  title: string
  description?: string
  action?: React.ReactNode
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
```

### Data Table (Simple)

```tsx
interface Column<T> {
  header: string
  accessor: keyof T | ((row: T) => React.ReactNode)
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyFn: (row: T) => string | number
}

export function DataTable<T>({ columns, data, keyFn }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={col.header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {data.map((row) => (
            <tr key={keyFn(row)} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col.header} className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                  {typeof col.accessor === 'function' ? col.accessor(row) : String(row[col.accessor] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

## Mock Data Pattern

Always create a `src/data/mock.ts` file with realistic data:

```typescript
// src/data/mock.ts

export interface User {
  id: string
  name: string
  email: string
  avatar: string
  role: 'admin' | 'member' | 'viewer'
  status: 'active' | 'inactive'
  lastSeen: string
}

export const users: User[] = [
  {
    id: '1',
    name: 'Sarah Chen',
    email: 'sarah@example.com',
    avatar: '',
    role: 'admin',
    status: 'active',
    lastSeen: '2 minutes ago',
  },
  // ... more items
]
```

## Icon Usage

Use `lucide-react` for all icons:

```tsx
import { Plus, Search, Settings, ChevronRight } from 'lucide-react'

// Inline
<Plus className="h-4 w-4" />

// With text
<button className="..."><Plus className="mr-2 h-4 w-4" /> Add Item</button>
```
```

**Step 3: Commit**

```bash
git add skills/
git commit -m "feat: add react-component-patterns skill with Tailwind components"
```

---

### Task 8: Wire skills into the agent configuration

**Objective:** Update `src/agent.py` to load the skills directories for both the orchestrator and react-developer subagent.

**Files:**
- Modify: `src/agent.py`

**Step 1: Update the `create_deep_agent` call to include skills**

In `src/agent.py`, add `skills` parameter and update the subagent to also use skills:

```python
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
```

**Step 2: Verify import still works**

```bash
cd ~/development/deepagent-1 && uv run python -c "from src.agent import agent; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add src/agent.py
git commit -m "feat: wire skills directories into agent and subagent config"
```

---

## Phase 2: React Chat Frontend

### Task 9: Scaffold the chat frontend with Vite

**Objective:** Create the React frontend project that will be the user's chat interface with the DeepAgent.

**Files:**
- Create: `frontend/` (entire Vite project)

**Step 1: Scaffold Vite+React+TS project**

```bash
cd ~/development/deepagent-1
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install core dependencies**

```bash
cd ~/development/deepagent-1/frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install @langchain/react @langchain/langgraph-sdk
npm install lucide-react
```

**Step 3: Configure Tailwind in `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:2024',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

**Step 4: Replace `frontend/src/index.css` with Tailwind imports**

```css
@import "tailwindcss";
```

**Step 5: Clean up template files**

```bash
rm -f ~/development/deepagent-1/frontend/src/App.css
rm -rf ~/development/deepagent-1/frontend/src/assets
```

**Step 6: Verify frontend builds**

```bash
cd ~/development/deepagent-1/frontend && npm run build
```

Expected: Build succeeds with no errors.

**Step 7: Commit**

```bash
cd ~/development/deepagent-1
git add frontend/
git commit -m "feat: scaffold chat frontend with Vite+React+Tailwind+LangGraph SDK"
```

---

### Task 10: Create the LangGraph client hook

**Objective:** Build a custom hook that wraps `@langchain/react` `useStream` with the DeepAgent-specific config.

**Files:**
- Create: `frontend/src/hooks/useDeepAgent.ts`

**Step 1: Create the hooks directory**

```bash
mkdir -p ~/development/deepagent-1/frontend/src/hooks
```

**Step 2: Create `frontend/src/hooks/useDeepAgent.ts`**

```typescript
import { useStream } from '@langchain/react'
import type { CompiledStateGraph } from '@langchain/langgraph-sdk'

// The DeepAgent graph type — messages-based state
interface DeepAgentState {
  messages: Array<{
    role: string
    content: string
    type: string
    name?: string
    id?: string
    tool_calls?: Array<{
      name: string
      args: Record<string, unknown>
      id: string
    }>
    additional_kwargs?: Record<string, unknown>
  }>
  todos?: Array<{
    id: string
    content: string
    status: string
  }>
}

const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL || 'http://127.0.0.1:2024'
const ASSISTANT_ID = import.meta.env.VITE_ASSISTANT_ID || 'deepagent'

export function useDeepAgent() {
  const stream = useStream<DeepAgentState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
    filterSubagentMessages: true,
  })

  const sendMessage = (content: string) => {
    stream.submit(
      { messages: [{ content, type: 'human' }] },
      { streamSubgraphs: true },
    )
  }

  return {
    ...stream,
    sendMessage,
    // Convenience accessors
    messages: stream.messages ?? [],
    isLoading: stream.isLoading,
    error: stream.error,
    interrupt: stream.interrupt,
    subagents: stream.subagents,
  }
}

export type { DeepAgentState }
```

**Step 3: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/hooks/
git commit -m "feat: add useDeepAgent hook wrapping @langchain/react useStream"
```

---

### Task 11: Build the ChatMessage component

**Objective:** Render individual chat messages (human, AI, tool results) with appropriate styling.

**Files:**
- Create: `frontend/src/components/ChatMessage.tsx`

**Step 1: Create the components directory**

```bash
mkdir -p ~/development/deepagent-1/frontend/src/components
```

**Step 2: Create `frontend/src/components/ChatMessage.tsx`**

```tsx
import { Bot, User, Wrench } from 'lucide-react'

interface ChatMessageProps {
  message: {
    type?: string
    role?: string
    content: string | Array<{ type: string; text?: string }>
    name?: string
    tool_calls?: Array<{ name: string; args: Record<string, unknown>; id: string }>
   additional_kwargs?: Record<string, unknown>
  }
}

function extractContent(content: string | Array<{ type: string; text?: string }>): string {
  if (typeof content === 'string') return content
  return content
    .filter((block) => block.type === 'text' && block.text)
    .map((block) => block.text!)
    .join('\n')
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isHuman = message.type === 'human' || message.role === 'user'
  const isTool = message.type === 'tool' || message.type === 'ToolMessage'
  const text = extractContent(message.content)

  if (isHuman) {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-3 text-sm text-white">
          {text}
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
          <User className="h-4 w-4" />
        </div>
      </div>
    )
  }

  if (isTool) {
    return (
      <div className="flex gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700">
          <Wrench className="h-4 w-4" />
        </div>
        <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 font-mono whitespace-pre-wrap">
          {message.name && <span className="text-xs font-semibold text-amber-600 block mb-1">{message.name}</span>}
          {text.slice(0, 500)}{text.length > 500 ? '...' : ''}
        </div>
      </div>
    )
  }

  // AI message
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-600">
        <Bot className="h-4 w-4" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-sm text-gray-800 shadow-sm border border-gray-100">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">{text}</div>
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.tool_calls.map((tc) => (
              <span key={tc.id} className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                <Wrench className="h-3 w-3" />
                {tc.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 3: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/components/ChatMessage.tsx
git commit -m "feat: add ChatMessage component for human/AI/tool messages"
```

---

### Task 12: Build the ChatInput component

**Objective:** A text input with send button for submitting messages.

**Files:**
- Create: `frontend/src/components/ChatInput.tsx`

**Step 1: Create `frontend/src/components/ChatInput.tsx`**

```tsx
import { useState } from 'react'
import { SendHorizontal } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled = false, placeholder = 'Describe the app you want to build...' }: ChatInputProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-gray-200 bg-white px-4 py-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <SendHorizontal className="h-4 w-4" />
      </button>
    </form>
  )
}
```

**Step 2: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/components/ChatInput.tsx
git commit -m "feat: add ChatInput component with send button"
```

---

### Task 13: Build the SubagentStatus component

**Objective:** Show real-time status of running subagents (react-developer, etc.) with their messages and tool calls.

**Files:**
- Create: `frontend/src/components/SubagentStatus.tsx`

**Step 1: Create `frontend/src/components/SubagentStatus.tsx`**

```tsx
import { Loader2, CheckCircle2, XCircle, Clock, Wrench } from 'lucide-react'

interface SubagentInfo {
  status: 'pending' | 'running' | 'complete' | 'error'
  messages: Array<{ content: string | Array<{ type: string; text?: string }>; type?: string }>
  toolCalls?: Array<{ name: string; args: Record<string, unknown>; id: string }>
}

interface SubagentStatusProps {
  subagents: Map<string, SubagentInfo> | undefined
}

const statusConfig = {
  pending: { icon: Clock, label: 'Waiting', color: 'text-gray-500 bg-gray-50' },
  running: { icon: Loader2, label: 'Working', color: 'text-blue-600 bg-blue-50' },
  complete: { icon: CheckCircle2, label: 'Done', color: 'text-green-600 bg-green-50' },
  error: { icon: XCircle, label: 'Error', color: 'text-red-600 bg-red-50' },
}

export function SubagentStatus({ subagents }: SubagentStatusProps) {
  if (!subagents || subagents.size === 0) return null

  const entries = Array.from(subagents.entries())

  return (
    <div className="space-y-2 px-4">
      {entries.map(([name, info]) => {
        const config = statusConfig[info.status]
        const Icon = config.icon
        const toolNames = info.toolCalls?.map((tc) => tc.name) ?? []

        return (
          <div key={name} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${config.color}`}>
            <Icon className={`h-4 w-4 shrink-0 ${info.status === 'running' ? 'animate-spin' : ''}`} />
            <span className="font-medium">{name}</span>
            <span className="text-xs opacity-70">{config.label}</span>
            {toolNames.length > 0 && (
              <div className="ml-auto flex gap-1">
                {toolNames.map((tn) => (
                  <span key={tn} className="inline-flex items-center gap-0.5 rounded bg-white/60 px-1.5 py-0.5 text-xs font-mono">
                    <Wrench className="h-2.5 w-2.5" />
                    {tn}
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

**Step 2: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/components/SubagentStatus.tsx
git commit -m "feat: add SubagentStatus component for live subagent tracking"
```

---

### Task 14: Build the main App component (chat interface)

**Objective:** Assemble all components into the main chat UI with message list, input, and subagent status.

**Files:**
- Create: `frontend/src/App.tsx`

**Step 1: Create `frontend/src/App.tsx`**

```tsx
import { useRef, useEffect } from 'react'
import { Bot } from 'lucide-react'
import { useDeepAgent } from './hooks/useDeepAgent'
import { ChatMessage } from './components/ChatMessage'
import { ChatInput } from './components/ChatInput'
import { SubagentStatus } from './components/SubagentStatus'

export default function App() {
  const { messages, isLoading, subagents, sendMessage, error } = useDeepAgent()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-gray-900">DeepAgent</h1>
          <p className="text-xs text-gray-500">React frontend generator — describe it, I build it</p>
        </div>
        {isLoading && (
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
            Thinking...
          </span>
        )}
      </header>

      {/* Subagent status bar */}
      <SubagentStatus subagents={subagents} />

      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
          Error: {error.message || String(error)}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-lg">
              <Bot className="h-8 w-8" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">What should I build?</h2>
              <p className="mt-1 text-sm text-gray-500">
                Describe a web app and I'll generate a working React frontend.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 text-sm">
              {['A task tracker', 'A weather dashboard', 'A recipe app', 'A habit tracker'].map((example) => (
                <button
                  key={example}
                  onClick={() => sendMessage(`Build me ${example.toLowerCase()} with React`)}
                  className="rounded-full border border-gray-200 bg-white px-4 py-2 text-gray-600 transition-colors hover:bg-gray-50 hover:border-gray-300"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-4">
          {messages.map((msg, i) => (
            <ChatMessage key={msg.id ?? i} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="mx-auto w-full max-w-3xl">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}
```

**Step 2: Update `frontend/src/main.tsx` to be clean**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**Step 3: Verify frontend builds**

```bash
cd ~/development/deepagent-1/frontend && npm run build
```

Expected: Build succeeds.

**Step 4: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/
git commit -m "feat: add main App, ChatMessage, ChatInput, SubagentStatus components"
```

---

### Task 15: Add environment variable config for the frontend

**Objective:** Allow the frontend to point at different LangGraph Server URLs.

**Files:**
- Create: `frontend/.env.example`
- Create: `frontend/.env`

**Step 1: Create `frontend/.env.example`**

```env
VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
VITE_ASSISTANT_ID=deepagent
```

**Step 2: Create `frontend/.env` (for local dev)**

```env
VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
VITE_ASSISTANT_ID=deepagent
```

**Step 3: Add `frontend/.env` to `.gitignore` (we already ignore `.env*` at root, but frontend also needs it)**

Ensure `frontend/.env` is in `.gitignore`. Check:

```bash
grep -r "\.env" ~/development/deepagent-1/.gitignore
```

If `.env` pattern isn't catching `frontend/.env`, add it explicitly.

**Step 4: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/.env.example frontend/src/vite-env.d.ts
git commit -m "feat: add .env.example for frontend LangGraph Server config"
```

---

## Phase 3: Integration & Verification

### Task 16: Update AGENTS.md with the new architecture

**Objective:** Document the full stack so future agents (and humans) understand the system.

**Files:**
- Modify: `AGENTS.md`

**Step 1: Rewrite `AGENTS.md`**

```markdown
# Agent instructions for deepagent-1

A full-stack Deep Agent system: a LangGraph-backed agent that generates React frontends from natural language, served via LangGraph Server and consumed by a React chat UI.

## Stack

- **Backend**: Python 3.11+, `deepagents>=0.4.8`, `langchain-ollama`, LangGraph Server
- **Chat Frontend**: React 19, TypeScript, Tailwind CSS 4, Vite, `@langchain/react`, `@langchain/langgraph-sdk`
- **Models**: Ollama Cloud (`glm-5:cloud` orchestrator, `qwen3.5:cloud` react-developer subagent)
- **Package / env**: [uv](https://docs.astral.sh/uv/)
- **Tasks**: [just](https://github.com/casey/just) — see `justfile`

## Architecture

```
User → React Chat UI (frontend/)
         ↓ SSE (LangGraph Server API)
       DeepAgent (src/agent.py)
         ↓ task tool
       react-developer subagent
         ↓ write_file / execute tools
       Vite+React project (generated, on disk)
         ↓ npm run dev
       Working app on localhost:5173
```

## Run the system

### 1. Start LangGraph Server

```bash
just server
# or: uv run langgraph dev
# Serves on http://127.0.0.1:2024
```

### 2. Start the chat frontend

```bash
cd frontend && npm run dev
# Serves on http://localhost:5173
```

### 3. Use it

Open http://localhost:5173, type a description like "Build me a task tracker app", and watch the agent scaffold and serve a React frontend.

### 4. CLI (alternative)

```bash
just run                                    # default prompt
just run-prompt "Build me a weather app"    # custom prompt
```

## Project layout

| Path | Role |
|------|------|
| `src/agent.py` | Agent graph definition (exported for LangGraph Server) |
| `main.py` | CLI entry point (backward compat) |
| `langgraph.json` | LangGraph Server config |
| `skills/` | Agent skill files loaded by SkillsMiddleware |
| `skills/react-scaffolding/` | Vite+React+Tailwind setup instructions |
| `skills/react-component-patterns/` | UI component patterns |
| `frontend/` | React chat UI (Vite+React+TS+Tailwind) |
| `pyproject.toml` | Python project metadata and dependencies |
| `justfile` | Task runner recipes |
| `.env` | Local env vars (gitignored) |

## Models

Override models via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_MODEL` | `glm-5:cloud` | Main agent routing/planning |
| `REACT_DEV_MODEL` | `qwen3.5:cloud` | Code generation subagent |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

Available Ollama Cloud models: `glm-5:cloud`, `nematron-3-super:cloud`, `qwen3.5:cloud`, `minimax-m2.7:cloud`, `minimax-m2.5:cloud`

## Verification

1. `uv run python -c "from src.agent import agent; print('OK')"` — agent imports cleanly
2. `cd frontend && npm run build` — chat UI builds
3. `just server` — LangGraph Server starts on :2024
4. End-to-end: open chat UI, send a prompt, see agent respond

## Guidelines for code changes

- Agent code lives in `src/agent.py`; skills in `skills/`
- Chat UI lives in `frontend/`
- After Python dependency changes: `uv sync`
- After JS dependency changes: `cd frontend && npm install`
- Do not commit `.env` files — use `.env.example` for documentation
```

**Step 2: Commit**

```bash
cd ~/development/deepagent-1 && git add AGENTS.md
git commit -m "docs: rewrite AGENTS.md with full-stack architecture docs"
```

---

### Task 17: Integration test — verify LangGraph Server starts

**Objective:** Prove that `langgraph dev` can load the agent graph and the server is reachable.

**Files:** No new files — verification only.

**Step 1: Start LangGraph Server in the background**

```bash
cd ~/development/deepagent-1 && uv run langgraph dev &
```

**Step 2: Wait for it to start (5 seconds), then test the API**

```bash
sleep 5
curl -s http://127.0.0.1:2024/ok
```

Expected: `{"ok":true}` or similar health check response.

**Step 3: List assistants**

```bash
curl -s http://127.0.0.1:2024/assistants/search | python3 -m json.tool
```

Expected: JSON array containing an assistant with id "deepagent".

**Step 4: Stop the server**

```bash
kill %1
```

**Step 5: No commit needed (verification only)**

---

### Task 18: Integration test — verify frontend connects to LangGraph Server

**Objective:** Prove the React chat UI can communicate with the LangGraph Server.

**Files:** No new files — verification only.

**Step 1: Start LangGraph Server**

```bash
cd ~/development/deepagent-1 && uv run langgraph dev &
```

**Step 2: Start the frontend dev server**

```bash
cd ~/development/deepagent-1/frontend && npm run dev &
```

**Step 3: Open the frontend in a browser**

```bash
open http://localhost:5173
```

**Step 4: Verify the chat UI loads**

The page should show the DeepAgent logo, "What should I build?" prompt, and example suggestions.

**Step 5: Clean up background processes**

```bash
kill %1 %2
```

**Step 6: No commit needed (verification only)**

---

### Task 19: End-to-end test — generate a React app via the agent

**Objective:** Send a real prompt through the chat UI and verify the agent generates a working React frontend.

**Files:** No new files — verification only.

**Step 1: Start LangGraph Server**

```bash
cd ~/development/deepagent-1 && uv run langgraph dev &
```

**Step 2: Start the frontend**

```bash
cd ~/development/deepagent-1/frontend && npm run dev &
```

**Step 3: In the chat UI, type: "Build me a simple counter app"**

**Step 4: Observe:**
- Agent responds with a delegation to the react-developer subagent
- SubagentStatus shows "react-developer" with "Working" status
- Tool calls flash by (write_file, execute, etc.)
- Agent reports the URL of the generated app

**Step 5: Open the generated app URL** (likely `http://localhost:5174` or similar)

**Step 6: Verify the generated app**
- Counter increments/decrements
- UI looks polished (Tailwind styled)
- No console errors

**Step 7: Clean up**

```bash
kill %1 %2
```

**Step 8: No commit needed (verification only)**

---

### Task 20: Hardening — add error boundaries and loading states

**Objective:** Make the chat UI robust against errors and slow responses.

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Add an error boundary to `frontend/src/App.tsx`**

Wrap the main App content in a React error boundary. Add this class component:

```tsx
import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-gray-50 p-8">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900">Something went wrong</h2>
            <p className="mt-2 text-sm text-gray-500">{this.state.error?.message}</p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

Then wrap the App export:

```tsx
export default function App() {
  return (
    <ErrorBoundary>
      {/* ... existing App content ... */}
    </ErrorBoundary>
  )
}
```

**Step 2: Verify frontend still builds**

```bash
cd ~/development/deepagent-1/frontend && npm run build
```

**Step 3: Commit**

```bash
cd ~/development/deepagent-1 && git add frontend/src/App.tsx
git commit -m "feat: add error boundary to chat UI"
```

---

## Phase 4: Update justfile with frontend commands

### Task 21: Add frontend dev/build/start recipes to justfile

**Objective:** Make it easy to manage both backend and frontend from the project root.

**Files:**
- Modify: `justfile`

**Step 1: Add these recipes to the end of the justfile**

```just
# --- Frontend commands ---

# Install frontend dependencies
fe-install:
    cd frontend && npm install

# Start frontend dev server
fe-dev:
    cd frontend && npm run dev

# Build frontend for production
fe-build:
    cd frontend && npm run build

# Preview production build
fe-preview:
    cd frontend && npm run preview

# --- Full stack ---

# Start both LangGraph Server and frontend (requires two terminals or tmux)
dev:
    @echo "In terminal 1: just server"
    @echo "In terminal 2: just fe-dev"
    @echo "Chat UI: http://localhost:5173"
    @echo "LangGraph API: http://127.0.0.1:2024"
```

**Step 2: Verify justfile parses**

```bash
cd ~/development/deepagent-1 && just --list
```

**Step 3: Commit**

```bash
cd ~/development/deepagent-1 && git add justfile
git commit -m "feat: add frontend and full-stack recipes to justfile"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| Phase 0: Restructure | Tasks 1-5 | Agent in `src/`, LangGraph Server, `.env`, updated justfile |
| Phase 1: Agent Skills | Tasks 6-8 | react-scaffolding + react-component-patterns skills wired into agent |
| Phase 2: Chat Frontend | Tasks 9-15 | Full React chat UI with useDeepAgent, ChatMessage, ChatInput, SubagentStatus |
| Phase 3: Integration | Tasks 16-20 | Documentation, server verification, end-to-end test, error boundary |
| Phase 4: Polish | Task 21 | justfile recipes for full-stack workflow |

**Total: 21 tasks, each 2-5 minutes of focused work.**