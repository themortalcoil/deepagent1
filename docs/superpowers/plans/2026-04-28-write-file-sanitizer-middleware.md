# WriteFileSanitizer Middleware Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three stacked workarounds in `src/agent.py` (a `RobustFilesystemBackend` subclass, a `_PatchedWriteFileSchema` Pydantic class, and a monkey-patch on `FilesystemMiddleware._create_write_file_tool`) with a single `WriteFileSanitizer` `AgentMiddleware` that uses the documented `wrap_tool_call` hook.

**Architecture:** A new `src/middleware.py` defines `WriteFileSanitizer`, which intercepts `write_file` tool calls before Pydantic validation. It coerces dict/list content to JSON strings and rewrites host-absolute paths (e.g., `/Users/scott/output/foo/x.tsx`) into virtual paths (`/foo/x.tsx`). The middleware is wired into both the main agent and the `react-developer` subagent via `create_deep_agent(..., middleware=[...])`. After wiring, the old workarounds are removed from `src/agent.py` and a minimal pytest setup is added with 11 unit tests + a manual smoke-test paragraph in `AGENTS.md`.

**Tech Stack:** Python 3.11+, `deepagents>=0.4.8,<0.5.0`, `langchain.agents.middleware.AgentMiddleware`, `langgraph.prebuilt.tool_node.ToolCallRequest`, `pytest>=8`, `uv`.

**Spec:** `docs/superpowers/specs/2026-04-28-write-file-sanitizer-middleware-design.md`.

---

## File Structure

**Files to create:**

| Path | Responsibility |
|---|---|
| `src/middleware.py` | `WriteFileSanitizer` class + `_coerce_content_to_str` + `_sanitize_path` helpers (~65 lines) |
| `tests/__init__.py` | Empty package marker so pytest can resolve `tests.test_middleware` |
| `tests/test_middleware.py` | 11 unit tests exercising the helpers and the middleware (~80 lines including a small `_make_tool_call_request` helper) |

**Files to modify:**

| Path | Change |
|---|---|
| `src/agent.py` | Remove `_coerce_to_str`, `RobustFilesystemBackend`, `_PatchedWriteFileSchema`, monkey-patch on `FilesystemMiddleware._create_write_file_tool`. Import + wire `WriteFileSanitizer`. Replace `RobustFilesystemBackend(...)` with stock `FilesystemBackend(...)` and add `OUTPUT_DIR.mkdir(...)`. Result: ~65 lines, down from 278. |
| `pyproject.toml` | Add `pytest>=8` to `[dependency-groups] dev`. Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. |
| `justfile` | Add `just test` recipe. |
| `AGENTS.md` | Add "Middleware regression check" subsection to the existing "Verification" section. |

---

## Task 1: Set up pytest infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`

- [ ] **Step 1: Add pytest dev dep and pytest config to `pyproject.toml`**

Replace the contents of `pyproject.toml` with:

```toml
[project]
name = "deepagent-1"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "deepagents>=0.4.8,<0.5.0",
    "langchain-ollama>=1.0.1",
]

[tool.setuptools.packages.find]
include = ["src*"]

[dependency-groups]
dev = [
    "langgraph-cli[inmem]>=0.3",
    "pytest>=8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

The only changes are: `"pytest>=8"` added to `dev`, and the new `[tool.pytest.ini_options]` block at the bottom.

- [ ] **Step 2: Create empty `tests/__init__.py`**

```bash
touch tests/__init__.py
```

The file should be empty (0 bytes).

- [ ] **Step 3: Sync deps**

Run: `uv sync`
Expected: pytest installed; no errors. Verify with `uv run pytest --version` — should print a version `>=8`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/__init__.py uv.lock
git commit -m "chore: add pytest dev dep and tests/ package"
```

---

## Task 2: TDD `_coerce_content_to_str` helper

**Files:**
- Create: `src/middleware.py`
- Create: `tests/test_middleware.py`

- [ ] **Step 1: Create `src/middleware.py` with the module docstring and an empty stub for `_coerce_content_to_str`**

```python
"""Middleware that sanitizes write_file tool calls before they reach Pydantic."""

import json
import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest

logger = logging.getLogger(__name__)


def _coerce_content_to_str(content: Any) -> str:
    """Coerce dict/list/primitive content to a string for write_file."""
    raise NotImplementedError
```

- [ ] **Step 2: Write failing tests in `tests/test_middleware.py`**

Create the file with these contents:

```python
"""Unit tests for src.middleware."""

from src.middleware import _coerce_content_to_str


def test_coerce_content_passes_strings_through():
    assert _coerce_content_to_str("hello") == "hello"


def test_coerce_content_serializes_dicts_as_indented_json():
    assert _coerce_content_to_str({"a": 1}) == '{\n  "a": 1\n}'


def test_coerce_content_serializes_lists():
    assert _coerce_content_to_str([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"


def test_coerce_content_stringifies_other_primitives():
    assert _coerce_content_to_str(42) == "42"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 4 FAILED, all with `NotImplementedError`.

- [ ] **Step 4: Implement `_coerce_content_to_str`**

Replace the body of `_coerce_content_to_str` in `src/middleware.py`:

```python
def _coerce_content_to_str(content: Any) -> str:
    """Coerce dict/list/primitive content to a string for write_file."""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)
    return str(content)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/middleware.py tests/test_middleware.py
git commit -m "feat: add _coerce_content_to_str helper with tests"
```

---

## Task 3: TDD `_sanitize_path` helper

**Files:**
- Modify: `src/middleware.py`
- Modify: `tests/test_middleware.py`

- [ ] **Step 1: Add a stub for `_sanitize_path` to `src/middleware.py`**

Add this constant near the top of the file (after the `logger = ...` line) and a stub function (after `_coerce_content_to_str`):

```python
_HOST_PREFIXES = ("/Users/", "/home/", "/tmp/", "/var/", "/opt/", "/etc/")


def _sanitize_path(path: str) -> str:
    """Collapse host-absolute paths emitted by the model into virtual paths.

    Models occasionally emit paths like /Users/scott/output/foo/bar.tsx instead
    of /foo/bar.tsx. virtual_mode treats the leading "/" as anchored to
    root_dir, so those resolve to ~/.deepagent/output/Users/scott/output/foo/...
    — wrong location, but inside root_dir, so no exception fires. We rewrite
    them here.
    """
    raise NotImplementedError
```

- [ ] **Step 2: Add failing tests to `tests/test_middleware.py`**

Update the import at the top:

```python
from src.middleware import _coerce_content_to_str, _sanitize_path
```

Append to `tests/test_middleware.py`:

```python
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
    # We accept the fallthrough — file ends up at root_dir/etc/passwd, junk
    # location but inside the sandbox.
    assert _sanitize_path("/etc/passwd") == "/etc/passwd"
```

- [ ] **Step 3: Run tests to verify the new ones fail**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 4 PASSED (from Task 2), 5 FAILED (new ones), all with `NotImplementedError`.

- [ ] **Step 4: Implement `_sanitize_path`**

Replace the body of `_sanitize_path` in `src/middleware.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify all pass**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 9 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/middleware.py tests/test_middleware.py
git commit -m "feat: add _sanitize_path helper with tests"
```

---

## Task 4: TDD `WriteFileSanitizer` middleware class

**Files:**
- Modify: `src/middleware.py`
- Modify: `tests/test_middleware.py`

- [ ] **Step 1: Add a stub `WriteFileSanitizer` class to `src/middleware.py`**

Append at the bottom of the file:

```python
class WriteFileSanitizer(AgentMiddleware):
    """Coerce write_file content to str and sanitize host-absolute file_paths.

    Runs before tool args reach Pydantic validation, so dict content passes
    through and host paths get rewritten to virtual paths. No-op for other tools.
    """

    def _maybe_rewrite(self, request: ToolCallRequest) -> ToolCallRequest:
        raise NotImplementedError

    def wrap_tool_call(self, request, handler):
        return handler(self._maybe_rewrite(request))

    async def awrap_tool_call(self, request, handler):
        return await handler(self._maybe_rewrite(request))
```

- [ ] **Step 2: Add a test helper and two failing tests to `tests/test_middleware.py`**

Update the imports at the top:

```python
"""Unit tests for src.middleware."""

from langgraph.prebuilt.tool_node import ToolCallRequest

from src.middleware import WriteFileSanitizer, _coerce_content_to_str, _sanitize_path


def _make_tool_call_request(name: str, args: dict) -> ToolCallRequest:
    """Build a minimal ToolCallRequest for tests.

    The middleware only reads tool_call["name"] and tool_call["args"]. The
    tool, state, and runtime fields can be None — Python doesn't enforce the
    dataclass type hints at runtime, and request.override() uses
    dataclasses.replace which only re-runs __init__ with the same fields.
    """
    tool_call = {"name": name, "args": args, "id": "test-call-id", "type": "tool_call"}
    return ToolCallRequest(tool_call=tool_call, tool=None, state=None, runtime=None)
```

Append to the bottom of the file:

```python
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
        args={
            "file_path": "/Users/scott/output/foo/x.json",
            "old_string": "a",
            "new_string": "b",
        },
    )
    sanitizer.wrap_tool_call(request, fake_handler)
    # Non-write_file tools are NOT rewritten by this middleware.
    assert captured["args"]["file_path"] == "/Users/scott/output/foo/x.json"
```

- [ ] **Step 3: Run tests to verify the new ones fail**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 9 PASSED (from Tasks 2-3), 2 FAILED (new ones), with `NotImplementedError`.

- [ ] **Step 4: Implement `_maybe_rewrite`**

Replace the body of `_maybe_rewrite` in `src/middleware.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify all 11 pass**

Run: `uv run pytest tests/test_middleware.py -v`
Expected: 11 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/middleware.py tests/test_middleware.py
git commit -m "feat: add WriteFileSanitizer middleware with tests"
```

---

## Task 5: Wire `WriteFileSanitizer` into `src/agent.py` (additive)

**Files:**
- Modify: `src/agent.py:11` (add import after existing deepagents import)
- Modify: `src/agent.py:250-279` (the `create_deep_agent(...)` call and subagent spec)

This task is additive — the old workarounds (`RobustFilesystemBackend`, `_PatchedWriteFileSchema`, monkey-patch) stay in place. After this task, both layers are active; the middleware runs first so the old layers become dormant. Removal happens in Task 6.

- [ ] **Step 1: Add import for `WriteFileSanitizer`**

In `src/agent.py`, after line 16 (the `from pydantic import BaseModel, field_validator` line), add:

```python
from src.middleware import WriteFileSanitizer
```

The imports block now ends with that line.

- [ ] **Step 2: Add `middleware=[WriteFileSanitizer()]` to the `create_deep_agent(...)` call**

In `src/agent.py`, find the `create_deep_agent(` block starting at line 250. After the existing `backend=backend,` argument and before `subagents=[`, add a new line:

```python
    middleware=[WriteFileSanitizer()],
```

- [ ] **Step 3: Add `"middleware": [WriteFileSanitizer()]` to the `react-developer` subagent spec**

In the same `create_deep_agent(` call, the `subagents=[...]` list contains one dict with `"name": "react-developer"`. After the existing `"skills": [f"{SKILLS_DIR}/"],` line in that dict, add:

```python
            "middleware": [WriteFileSanitizer()],
```

After this step, the subagent spec block reads:

```python
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
```

- [ ] **Step 4: Verify the agent imports cleanly**

Run: `uv run python -c "from src.agent import agent; print('OK')"`
Expected: prints `OK` and exits 0. No tracebacks.

- [ ] **Step 5: Verify all unit tests still pass**

Run: `uv run pytest tests/ -v`
Expected: 11 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/agent.py
git commit -m "feat: wire WriteFileSanitizer into main agent and react-developer subagent"
```

---

## Task 6: Remove the old workarounds from `src/agent.py`

**Files:**
- Modify: `src/agent.py` (delete lines 6, 12-14, 16, 104-115, 118-204, 207-225, 228-243; replace lines 245-248)

After this task, the file is ~65 lines. The line numbers below refer to the file as it stands at the start of this task (i.e., after Task 5 added the import and wiring — that adds 2 lines, so the references that follow shift by 2 vs. the original file. To avoid confusion, the steps below describe each removal by the **identifier being removed**, not by line number.)

- [ ] **Step 1: Remove the `import json` line**

Delete the line `import json` (currently line 6 of the original file, line 6 still after Task 5).

- [ ] **Step 2: Remove the `Annotated` import**

Delete the line `from typing import Annotated`.

- [ ] **Step 3: Remove the deepagents internal imports that are no longer needed**

Delete these three lines:
```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import WriteResult
from deepagents.middleware.filesystem import FilesystemMiddleware
```

Replace them with a single line:
```python
from deepagents.backends.filesystem import FilesystemBackend
```

(`FilesystemBackend` is still needed for the new direct instantiation. `WriteResult` was only used by the subclass; `FilesystemMiddleware` was only used by the monkey-patch.)

- [ ] **Step 4: Remove the `pydantic` import**

Delete the line `from pydantic import BaseModel, field_validator`.

- [ ] **Step 5: Remove the `_coerce_to_str` helper**

Delete the function `def _coerce_to_str(v) -> str:` and its body (the entire definition, ~12 lines).

- [ ] **Step 6: Remove the `RobustFilesystemBackend` class**

Delete the entire `class RobustFilesystemBackend(FilesystemBackend):` block, including its docstring, `_HOST_PREFIXES` and `_STRIP_DIRS` class attributes, `__init__`, `_sanitize_path` classmethod, and `write` / `awrite` overrides (~85 lines).

- [ ] **Step 7: Remove the `_PatchedWriteFileSchema` class**

Delete the entire `class _PatchedWriteFileSchema(BaseModel):` block including its docstring, the `file_path` and `content` `Annotated` fields, `model_config`, and `_coerce_content_to_str` `field_validator` (~18 lines).

- [ ] **Step 8: Remove the monkey-patch on `FilesystemMiddleware._create_write_file_tool`**

Delete this block (lines starting with `# Monkey-patch ...` comment, the `_original_create_write_file_tool = ...`, the `def _patched_create_write_file_tool(self):` function, and the assignment `FilesystemMiddleware._create_write_file_tool = _patched_create_write_file_tool`). About 16 lines including comments.

- [ ] **Step 9: Replace `RobustFilesystemBackend(...)` with stock `FilesystemBackend(...)` and add `OUTPUT_DIR.mkdir(...)`**

Find the block:
```python
backend = RobustFilesystemBackend(
    root_dir=str(OUTPUT_DIR),
    virtual_mode=True,
)
```

Replace it with:
```python
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

backend = FilesystemBackend(root_dir=str(OUTPUT_DIR), virtual_mode=True)
```

(The `mkdir` call replaces the work the subclass `__init__` was doing. It can also be placed immediately after the `OUTPUT_DIR = Path(...)` assignment near the top of the file — either location works; pick the one that reads more clearly.)

- [ ] **Step 10: Verify no stragglers**

Run: `grep -n "RobustFilesystemBackend\|_PatchedWriteFileSchema\|_coerce_to_str\|_create_write_file_tool\|FilesystemMiddleware\|field_validator\|BaseModel\|Annotated\|WriteResult" src/agent.py`
Expected: no output (the grep finds nothing).

If any line is found, return to the appropriate step and finish the deletion.

- [ ] **Step 11: Verify line count**

Run: `wc -l src/agent.py`
Expected: under 100 lines (target ~65).

- [ ] **Step 12: Verify the agent still imports cleanly**

Run: `uv run python -c "from src.agent import agent; print('OK')"`
Expected: prints `OK`. No tracebacks.

- [ ] **Step 13: Verify all unit tests still pass**

Run: `uv run pytest tests/ -v`
Expected: 11 PASSED.

- [ ] **Step 14: Commit**

```bash
git add src/agent.py
git commit -m "refactor: remove RobustFilesystemBackend, _PatchedWriteFileSchema, and monkey-patch in favor of WriteFileSanitizer"
```

---

## Task 7: Add `just test` recipe and AGENTS.md smoke-test docs

**Files:**
- Modify: `justfile`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add `just test` recipe**

Open `justfile`. Find the `# --- Frontend commands ---` section (around line 53). Just above it, add:

```
# --- Tests ---

# Run unit tests
test:
    uv run pytest tests/

```

- [ ] **Step 2: Verify `just test` works**

Run: `just test`
Expected: `11 passed in <1s` (or similar).

- [ ] **Step 3: Add manual smoke-test paragraph to `AGENTS.md`**

Open `AGENTS.md`. Find the `## Verification` section (currently has 4 numbered items, ending with "End-to-end: open chat UI, send a prompt, see agent respond"). Add a fifth item:

```markdown
5. **Middleware regression check**: With `just server` running, send a prompt like "Build me a counter app" via the chat UI. After the agent finishes:

   - `ls ~/.deepagent/output/<project-name>/` should show `package.json` + `src/` (regular project files).
   - `ls ~/.deepagent/output/Users/` should NOT exist — if it does, sanitization regressed.
   - `cat ~/.deepagent/output/<project-name>/package.json | jq .` should succeed — if it fails with a JSON parse error, dict-coercion regressed.
   - Check `langgraph dev` server logs for `WriteFileSanitizer:` lines — these indicate which workarounds are still firing on the current model. Useful as input for a future PR that decides whether to delete the workarounds entirely.
```

- [ ] **Step 4: Verify `AGENTS.md` is well-formed**

Run: `head -150 AGENTS.md` and visually confirm the new section reads cleanly.

- [ ] **Step 5: Final acceptance check — confirm the full spec acceptance criteria**

Run all of these and confirm each:

```bash
# 1. agent.py is under 100 lines
wc -l src/agent.py
# Expected: ≤ 100

# 2. agent.py does not import from deepagents.middleware.filesystem or pydantic
grep -E "from deepagents\.middleware\.filesystem|from pydantic" src/agent.py
# Expected: no output

# 3. No assignment to FilesystemMiddleware._create_write_file_tool
grep -E "FilesystemMiddleware\._create_write_file_tool *=" src/agent.py src/middleware.py
# Expected: no output

# 4. All unit tests pass
uv run pytest tests/ -v
# Expected: 11 passed

# 5. Agent imports cleanly
uv run python -c "from src.agent import agent; print('OK')"
# Expected: OK

# 6. Frontend still builds (no regressions — should be unaffected)
cd frontend && npm run build && cd ..
# Expected: build succeeds
```

If any of these fail, identify the root cause before proceeding. The acceptance criteria from the spec must all hold.

- [ ] **Step 6: Commit**

```bash
git add justfile AGENTS.md
git commit -m "docs: add just test recipe and middleware regression check to AGENTS.md"
```

---

## Self-Review

**Spec coverage:**
- Spec "Approach" → Task 4 (WriteFileSanitizer + wrap_tool_call). ✓
- Spec "Architecture: what changes / what stays" → Tasks 5-6 (additive wiring + removal). ✓
- Spec "Components: src/middleware.py" → Tasks 2-4. ✓
- Spec "Components: src/agent.py refactored" → Task 6 (and Task 5 wires the import). ✓
- Spec "Data flow" → Implicit in Task 4 tests (rewrite + passthrough). ✓
- Spec "Error handling" → Tests in Task 4 cover write_file vs other tools; the no-try/except posture is in the implementation in Task 4 step 4. ✓
- Spec "Testing: unit tests" → Tasks 2, 3, 4 (4 + 5 + 2 = 11 tests). ✓
- Spec "Testing: pytest setup" → Task 1. ✓
- Spec "Testing: manual smoke test" → Task 7. ✓
- Spec "Build sequence" → Tasks 2-4 (add middleware), Task 5 (wire), Task 6 (remove), Task 7 (tests + docs). ✓
- Spec "Acceptance criteria" → Task 7 step 5 explicit checks. ✓

**Placeholder scan:** No "TBD", "TODO", "implement later", or vague steps. Every code block is complete. Every command has expected output. ✓

**Type / name consistency:**
- `WriteFileSanitizer` (class name) — consistent across Tasks 4, 5, 6. ✓
- `_coerce_content_to_str` (function) — consistent across Tasks 2, 4 (used internally), tests. ✓
- `_sanitize_path` (function) — consistent across Tasks 3, 4 (used internally), tests. ✓
- `_make_tool_call_request` (test helper) — defined in Task 4 step 2, used in Task 4 step 2. ✓
- `_HOST_PREFIXES` (constant) — defined in Task 3 step 1, used by `_sanitize_path` in Task 3 step 4. ✓
- `_maybe_rewrite` (method) — stub in Task 4 step 1, real impl in Task 4 step 4. ✓

No issues found.
