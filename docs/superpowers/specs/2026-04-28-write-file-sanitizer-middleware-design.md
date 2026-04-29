# Design: Replace defensive `write_file` workarounds with a `wrap_tool_call` middleware

**Date:** 2026-04-28
**Branch:** feature/fe-harness
**Scope:** Backend-only refactor of `src/agent.py` (no frontend changes)
**Stage:** D — staged backend cleanup; subagent + UI architecture preserved.

## Problem

`src/agent.py` is 279 lines, of which roughly 120 are defensive scaffolding around two model bugs:

1. **Dict `content` on `write_file`** — some models pass `content` as a `dict` instead of a `str`. The default `WriteFileSchema` validates `content: str` and rejects dicts at the Pydantic layer before the backend ever sees them.
2. **Host-absolute `file_path` on `write_file`** — models occasionally emit paths like `/Users/scott/output/foo/x.tsx` instead of `/foo/x.tsx`. With `virtual_mode=True`, the leading `/` is anchored to `root_dir`, so these resolve to `~/.deepagent/output/Users/scott/output/foo/x.tsx` — wrong location, but inside `root_dir` so no exception fires.

The current code addresses both via three stacked layers:

- A `RobustFilesystemBackend` subclass overriding `write` / `awrite` (~80 lines incl. the 50-line `_sanitize_path` heuristic with five strategies).
- A `_PatchedWriteFileSchema` Pydantic class with a `field_validator(mode="before")` for content coercion.
- A monkey-patch on `FilesystemMiddleware._create_write_file_tool` that swaps in the patched schema across all three internal `FilesystemMiddleware` instantiations (general-purpose, subagent, main).

Each layer was added in response to escalating bugs (commits `7cfdb28` → `42b1b26` → `aa860b5`). The layers stack — `_coerce_to_str` runs at *both* the schema and the backend level, redundantly.

## Goals

This refactor pursues three motivations together:

- **A. Reduce code volume and conceptual complexity.** Fewer "why is this here?" comments; easier for future-you to read end-to-end.
- **B. Eliminate fragile defensive scaffolding.** Replace papered-over workarounds with a single, focused, idiomatic implementation.
- **C. Replace fragile patterns with a proper deepagents/langchain extension API.** Specifically: stop monkey-patching `FilesystemMiddleware._create_write_file_tool`, since that breaks the moment deepagents 0.5.0 changes the internal API.

## Non-goals

- Collapsing the orchestrator → react-developer subagent split (deferred per Q2 stage-D decision).
- Frontend changes to `SubagentStatus`, `useDeepAgent.ts`, or the chat UI.
- Empirical deletion of the workarounds (deferred per Q3 — this PR replaces; a future PR can decide whether to delete based on logs).
- Changes to system prompts, skills, the `_build_model` helper, or `OUTPUT_DIR` semantics.

## Approach

Use `langchain.agents.middleware.AgentMiddleware.wrap_tool_call` — the documented hook that intercepts a tool call **before** `tool.invoke()` triggers Pydantic validation. Confirmed at `langgraph/prebuilt/tool_node.py:933-938`: `wrap_tool_call` runs the handler, the handler calls `tool.invoke(call_args, config)`, and Pydantic validation happens inside `invoke()`. So a middleware that rewrites `request.tool_call["args"]` lets us coerce `content` and sanitize `file_path` *before* validation, fixing both bugs in one place with no monkey-patching.

This replaces:
- `RobustFilesystemBackend` subclass → unsubclassed `FilesystemBackend(root_dir=..., virtual_mode=True)`.
- `_PatchedWriteFileSchema` and the monkey-patch → deleted.
- `_coerce_to_str` standalone helper → moved into `src/middleware.py` as a private function.

## Architecture

### What changes

`src/agent.py` collapses from **279 → ~65 lines** by:

- **Removing:** `RobustFilesystemBackend` (subclass + 50-line `_sanitize_path`), `_PatchedWriteFileSchema`, the monkey-patch on `FilesystemMiddleware._create_write_file_tool`, and the standalone `_coerce_to_str`.
- **Adding:** A new `src/middleware.py` (~65 lines) containing `WriteFileSanitizer`, plus a one-line `OUTPUT_DIR.mkdir(...)` in `agent.py` to replace the work the subclass `__init__` did.

### Where the middleware is wired

Two places, because `create_deep_agent` builds two parallel middleware stacks:

1. **Main agent**: `create_deep_agent(..., middleware=[WriteFileSanitizer()])` — appended to `deepagent_middleware` per `graph.py:269`.
2. **React-developer subagent**: `subagents=[{..., "middleware": [WriteFileSanitizer()]}]` — appended to `subagent_middleware` per `graph.py:230`.

Two separate stateless instances. The general-purpose subagent (auto-built by `create_deep_agent`) is not wired because it is never invoked in this app.

### What stays untouched

- Orchestrator → react-developer split.
- `OUTPUT_DIR` env var, virtual-mode sandboxing, skills paths.
- `_build_model` helper.
- Frontend, skills, langgraph.json, justfile.
- The orchestrator's anti-over-delegation system prompt.

## Components

### `src/middleware.py` — new file (~65 lines)

```python
"""Middleware that sanitizes write_file tool calls before they reach Pydantic."""

import json
import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest

logger = logging.getLogger(__name__)

_HOST_PREFIXES = ("/Users/", "/home/", "/tmp/", "/var/", "/opt/", "/etc/")


def _coerce_content_to_str(content: Any) -> str:
    """Coerce dict/list/primitive content to a string for write_file."""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)
    return str(content)


def _sanitize_path(path: str) -> str:
    """Collapse host-absolute paths emitted by the model into virtual paths.

    Models occasionally emit paths like /Users/scott/output/foo/bar.tsx instead
    of /foo/bar.tsx. virtual_mode treats the leading "/" as anchored to
    root_dir, so those resolve to ~/.deepagent/output/Users/scott/output/foo/...
    — wrong location, but inside root_dir, so no exception fires. We rewrite
    them here.
    """
    if not path.startswith(_HOST_PREFIXES):
        return path
    idx = path.find("/output/")
    if idx >= 0:
        return path[idx + len("/output"):]  # leaves the leading "/"
    parts = Path(path).parts  # ('/', 'Users', 'scott', 'foo', 'bar.tsx')
    if path.startswith(("/Users/", "/home/")) and len(parts) > 3:
        return "/" + "/".join(parts[3:])
    if len(parts) > 2:
        return "/" + "/".join(parts[2:])
    return path


class WriteFileSanitizer(AgentMiddleware):
    """Coerce write_file content to str and sanitize host-absolute file_paths.

    Runs before tool args reach Pydantic validation, so dict content passes
    through and host paths get rewritten to virtual paths. No-op for other tools.
    """

    def _maybe_rewrite(self, request: ToolCallRequest) -> ToolCallRequest:
        if request.tool_call["name"] != "write_file":
            return request
        args = dict(request.tool_call["args"])
        original_path = args.get("file_path")
        original_content = args.get("content")
        if original_content is not None:
            args["content"] = _coerce_content_to_str(original_content)
            if not isinstance(original_content, str):
                logger.info(
                    "WriteFileSanitizer: coerced content (type=%s) to str",
                    type(original_content).__name__,
                )
        if isinstance(original_path, str):
            sanitized = _sanitize_path(original_path)
            if sanitized != original_path:
                args["file_path"] = sanitized
                logger.info(
                    "WriteFileSanitizer: rewrote path %r -> %r",
                    original_path,
                    sanitized,
                )
        return request.override(tool_call={**request.tool_call, "args": args})

    def wrap_tool_call(self, request, handler):
        return handler(self._maybe_rewrite(request))

    async def awrap_tool_call(self, request, handler):
        return await handler(self._maybe_rewrite(request))
```

### `src/agent.py` — refactored (~65 lines)

```python
"""DeepAgent entry point for LangGraph Server."""

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_ollama import ChatOllama

from src.middleware import WriteFileSanitizer

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = str(_PROJECT_ROOT / "skills")

_DEFAULT_OUTPUT_DIR = Path.home() / ".deepagent" / "output"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR)))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek-v4-flash:cloud")
REACT_DEV_MODEL = os.environ.get("REACT_DEV_MODEL", "deepseek-v4-flash:cloud")

REACT_DEV_SYSTEM_PROMPT = """..."""  # unchanged from current code


def _build_model(model_name: str) -> ChatOllama:
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
```

## Data flow

### Happy path: well-formed call

`react-developer` calls `write_file(file_path="/counter-app/package.json", content="{...}")`:

1. Model emits the tool call → AIMessage with `tool_calls=[{"name": "write_file", "args": {...}, "id": ...}]`.
2. `ToolNode._run_one` builds a `ToolCallRequest` and invokes the chained `wrap_tool_call` middleware.
3. `WriteFileSanitizer.wrap_tool_call` runs: `_maybe_rewrite` checks the name is `write_file`, sees `content` is a `str` and `file_path` doesn't start with a host prefix → no rewrite, no log.
4. `handler(request)` → `tool.invoke(call_args, config)` → Pydantic validates `content: str` (passes) → `FilesystemMiddleware.sync_write_file` → `backend.write` → file written under `~/.deepagent/output/counter-app/package.json`.
5. `ToolMessage("Updated file /counter-app/package.json")` returned to the model.

Overhead: one dict lookup, one `startswith` check.

### Repair path: dict content + host path

Model emits `write_file(file_path="/Users/scott/output/foo-app/package.json", content={"name": "foo-app", "version": "1.0.0"})`:

1. `ToolCallRequest.tool_call["args"]` = `{"file_path": "/Users/scott/output/foo-app/package.json", "content": {...}}`.
2. `_maybe_rewrite`:
   - `_coerce_content_to_str({"name": ...})` → `'{\n  "name": "foo-app",\n  "version": "1.0.0"\n}'`.
   - `_sanitize_path("/Users/scott/output/foo-app/package.json")` → returns `"/foo-app/package.json"`.
   - INFO log fires twice.
3. `request.override(tool_call={**original, "args": rewritten_args})` → new immutable request.
4. `handler(request)` → Pydantic validates `content: str` (passes) → `backend.write("/foo-app/package.json", "...")` → writes to `~/.deepagent/output/foo-app/package.json`.

The model never sees the rewriting — only the success message. Future calls can still use the wrong format and still succeed.

### Edge case: tool not write_file

`_maybe_rewrite` returns the original request unchanged. Cost: one string equality check.

### Edge case: pathological content

`content=None` or `content` missing → `original_content is not None` guard prevents touching it → flows through to Pydantic's "field required" error → model retries with explicit error message.

### Edge case: path that doesn't match either strategy

`/etc/passwd` → fallthrough → returns path unchanged → resolves to `~/.deepagent/output/etc/passwd` (junk location but inside the sandbox). Acceptable tradeoff; stricter handling would risk model retry loops.

### Composition with other middleware

`WriteFileSanitizer` is appended after the deepagents-built stack (`TodoListMiddleware`, `MemoryMiddleware`, `SkillsMiddleware`, `FilesystemMiddleware`, `SubAgentMiddleware`, `SummarizationMiddleware`, `AnthropicPromptCachingMiddleware`, `PatchToolCallsMiddleware`). None of these implement `wrap_tool_call` today, so ordering doesn't currently matter. If deepagents adds a `wrap_tool_call` later, ordering should be re-verified.

## Error handling

### Errors NOT caught by the middleware

By design, `wrap_tool_call` runs the handler with `return handler(...)` — no `try/except`. Anything downstream propagates naturally:

| Error | Source | Model sees |
|---|---|---|
| Pydantic `ValidationError` (missing `file_path`/`content`) | `tool.invoke()` | `ToolInvocationError` → retries |
| `ValueError("Path traversal not allowed")` | `FilesystemBackend._resolve_path` | Tool error → retries |
| `ValueError("Path: ... outside root directory")` | `FilesystemBackend._resolve_path` | Tool error → retries |
| File already exists (`write_file` rejects overwrite) | `FilesystemMiddleware` | Error string telling model to use `edit_file` |
| Disk full / permission denied | `Path.write_text` in backend | OS error → wrapped |

Wrapping any of these would hide problems.

### Errors handled

Exactly two transformations, both specific to `write_file`:

1. Non-string `content` → coerced via `_coerce_content_to_str`.
2. Host-prefixed `file_path` → rewritten via `_sanitize_path`. Two strategies (output-marker, host-dir-strip), with a fallthrough for unmatched cases.

### Logging strategy

INFO-level on every actual rewrite, with the original value:

```
INFO  src.middleware  WriteFileSanitizer: coerced content (type=dict) to str
INFO  src.middleware  WriteFileSanitizer: rewrote path '/Users/scott/output/foo/x.tsx' -> '/foo/x.tsx'
```

Why INFO, not DEBUG: these are signals about model behavior, not implementation noise. If we ever want to remove the workarounds (a future PR), `grep WriteFileSanitizer` in the LangGraph Server logs is the data we need.

Why not WARNING: a rewrite is "expected and handled" given the current model + system prompt. WARNING would create alarm-fatigue.

To silence:
```python
logging.getLogger("src.middleware").setLevel(logging.WARNING)
```

### What can break that the design accepts

- **Non-JSON-serializable `content`** (e.g., circular reference): `json.dumps` raises `ValueError`, propagates as a tool error, model retries.
- **Pathological host path** sanitized incorrectly: file ends up in a wrong-but-sandboxed location. Strictly better than today's behavior (which writes to `~/.deepagent/output/Users/scott/...`).
- **Two `WriteFileSanitizer` instances on the chain** (main + subagent): No double-rewriting because the main agent's instance and the subagent's instance run in different `ToolNode`s. Cost: a second instantiation. If empirically wrong, drop the orchestrator-side instance.

### Explicitly NOT done

- **No retries inside the middleware.** `wrap_tool_call` supports it, but every error case here is either deterministic (model needs to see it) or one-shot rewriting.
- **No partial sanitization.** All transforms are independent and idempotent.
- **No telemetry/metrics**, just logs.

## Testing

### Unit tests — `tests/test_middleware.py` (~60 lines, 11 tests)

```python
from src.middleware import WriteFileSanitizer, _coerce_content_to_str, _sanitize_path

def test_sanitize_path_passes_virtual_paths_through():
    assert _sanitize_path("/foo-app/package.json") == "/foo-app/package.json"

def test_sanitize_path_strips_output_marker():
    assert _sanitize_path("/Users/scott/output/foo-app/x.tsx") == "/foo-app/x.tsx"

def test_sanitize_path_strips_user_home_when_no_output_marker():
    assert _sanitize_path("/Users/scott/foo-app/x.tsx") == "/foo-app/x.tsx"

def test_sanitize_path_strips_tmp_prefix():
    assert _sanitize_path("/tmp/foo-app/package.json") == "/foo-app/package.json"

def test_sanitize_path_falls_through_for_short_paths():
    # /etc/passwd has no /output/ marker and only one segment after /etc/.
    assert _sanitize_path("/etc/passwd") == "/etc/passwd"

def test_coerce_content_passes_strings_through():
    assert _coerce_content_to_str("hello") == "hello"

def test_coerce_content_serializes_dicts_as_indented_json():
    assert _coerce_content_to_str({"a": 1}) == '{\n  "a": 1\n}'

def test_coerce_content_serializes_lists():
    assert _coerce_content_to_str([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"

def test_coerce_content_stringifies_other_primitives():
    assert _coerce_content_to_str(42) == "42"

def test_middleware_rewrites_write_file_args():
    sanitizer = WriteFileSanitizer()
    captured = {}
    def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None
    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "content": {"k": "v"}},
    )
    sanitizer.wrap_tool_call(request, fake_handler)
    assert captured["args"]["file_path"] == "/foo/x.json"
    assert captured["args"]["content"] == '{\n  "k": "v"\n}'

def test_middleware_passes_through_other_tools():
    sanitizer = WriteFileSanitizer()
    captured = {}
    def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None
    request = _make_tool_call_request(
        name="edit_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "old_string": "a", "new_string": "b"},
    )
    sanitizer.wrap_tool_call(request, fake_handler)
    # Non-write_file tools are NOT rewritten by this middleware.
    assert captured["args"]["file_path"] == "/Users/scott/output/foo/x.json"
```

`_make_tool_call_request` is a small test helper that builds a `ToolCallRequest` with a stub `tool_call` dict. The actual `tool` and `state` fields can be `None` — `wrap_tool_call` only reads `tool_call["name"]` and `tool_call["args"]`.

11 tests, runs in <1 second.

### Pytest setup

- Add `pytest>=8` to `[dependency-groups] dev` in `pyproject.toml`.
- One-line `[tool.pytest.ini_options]` block with `testpaths = ["tests"]`.
- Add `tests/__init__.py` (empty).
- Add `just test` recipe: `uv run pytest tests/`.

No CI changes.

### Manual smoke test (documented in AGENTS.md)

Add to "Verification" section:

```
5. Middleware regression check:
   - just server (in one terminal)
   - Use the chat UI (or curl) to send "Build me a counter app".
   - After the run, verify:
     - ls ~/.deepagent/output/<project-name>/  shows package.json + src/
     - NOT ls ~/.deepagent/output/Users/  (would mean sanitization regressed)
     - cat ~/.deepagent/output/<project-name>/package.json | jq .  succeeds
       (would fail if dict-coercion regressed and Python-dict-style content leaked)
   - Check langgraph dev logs for "WriteFileSanitizer:" lines —
     these tell you if the workarounds are still triggering on the current model.
```

This is the only true end-to-end check. We don't try to automate it because (a) it requires a live Ollama Cloud connection and (b) the agent run is non-deterministic.

### Out of scope

- Frontend tests.
- Tests for the rest of `agent.py` (the `_build_model` helper, env var parsing).
- Integration tests that drive the full agent.
- Regression guard via `inspect.getsource(FilesystemMiddleware._create_write_file_tool)` — this would couple our test suite to deepagents internals, contradicting the principle that motivates this refactor.

## Build sequence

One PR, four commits in order:

1. **Add `src/middleware.py`** with `WriteFileSanitizer`, `_coerce_content_to_str`, `_sanitize_path`. No changes to other files. (~65 lines)
2. **Wire the middleware into `agent.py`** via `middleware=[...]` on `create_deep_agent` and on the `react-developer` subagent spec. Existing AGENTS.md verification still passes (the agent imports cleanly, the smoke run still works). The old workarounds are still in place but become dormant: the middleware runs first, so by the time `_PatchedWriteFileSchema` sees `content`, it is already a `str`, and by the time `RobustFilesystemBackend._sanitize_path` runs, the path has already been rewritten. Their branches never trigger.
3. **Remove the old workarounds**: delete `RobustFilesystemBackend`, `_PatchedWriteFileSchema`, the monkey-patch on `FilesystemMiddleware._create_write_file_tool`, the `_coerce_to_str` helper. Replace `RobustFilesystemBackend(...)` with `FilesystemBackend(root_dir=str(OUTPUT_DIR), virtual_mode=True)`. Add `OUTPUT_DIR.mkdir(parents=True, exist_ok=True)` to compensate for the removed `__init__` mkdir.
4. **Add tests + AGENTS.md update**: `tests/test_middleware.py`, `tests/__init__.py`, `pyproject.toml` dev dep, justfile `test` recipe, manual smoke-test paragraph.

Each commit individually leaves the agent in a working state.

## Acceptance criteria

- `src/agent.py` is < 100 lines and imports nothing from `deepagents.middleware.filesystem` or `pydantic`.
- No assignment to `FilesystemMiddleware._create_write_file_tool` anywhere in the repo (i.e., the monkey-patch is gone). References in design docs or commit messages are fine.
- `uv run pytest tests/` passes (11 tests).
- `uv run python -c "from src.agent import agent; print('OK')"` prints `OK` (existing AGENTS.md verification).
- `cd frontend && npm run build` succeeds (no frontend regressions — should be unaffected).
- Manual smoke test in AGENTS.md passes against `deepseek-v4-flash:cloud`.

## Open questions for implementation

None — design is fully specified. Implementation plan is the next deliverable.
