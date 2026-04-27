# Plan: Fix Monkey-Patches and TypeScript Build Errors

**Date:** 2026-04-26
**Branch:** feature/fe-harness

---

## Goal

Fix the two high-priority issues blocking a clean build so the project can be committed and merged to main:

1. Replace fragile monkey-patches in `src/agent.py` with a proper `RobustFilesystemBackend` subclass
2. Fix two TypeScript build errors in the frontend

---

## Current Context

### Issue 1: Monkey-patches in agent.py

The uncommitted `src/agent.py` has two monkey-patches at lines 59–102:

- **Lines 59–72**: Monkey-patches `FilesystemBackend.write` by capturing `_orig_write` and replacing it with `_patched_write`. This mutates the class globally — fragile and impure.
- **Lines 74–102**: Imports `WriteFileSchema` from `deepagents.middleware.filesystem`, creates a `PatchedWriteFileSchema` subclass, and replaces it globally on the module. This import may break on deepagents upgrades, and the global replacement is a code smell.

Both patches solve the same real problem: GLM models pass `write_file` content as a `dict` instead of a `str`, which crashes the default `FilesystemBackend`.

**Correct approach:** Subclass `FilesystemBackend`, override `write()` and `awrite()` to coerce content, and pass the subclass instance via the `backend=` parameter to `create_deep_agent()`. This is the intended extension pattern, avoids global mutation, and survives library upgrades.

### Issue 2: TypeScript build errors

Running `cd frontend && npm run build` produces two errors:

- **SubagentStatus.tsx:22** — `TS6133`: `isLoading` is destructured from props but never used in the component body.
- **useDeepAgent.ts:52** — `TS2322`: The patched `client.runs.stream` assignment has a type mismatch. The function signature `(threadId: string, ...)` doesn't satisfy the overloaded type which accepts `threadId: string | null`.

---

## Proposed Approach

### Fix 1: RobustFilesystemBackend subclass

Replace the entire monkey-patch block (lines 6, 11–13, 59–102) with a clean subclass:

```python
class RobustFilesystemBackend(FilesystemBackend):
    """FilesystemBackend that auto-serializes dict content to JSON strings.

    Some models (e.g., GLM) pass write_file content as a dict instead of a str.
    This subclass coerces any non-string content before delegating to the parent.
    """

    def write(self, file_path: str, content) -> WriteResult:
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)
        elif not isinstance(content, str):
            content = str(content)
        return super().write(file_path, content)

    async def awrite(self, file_path: str, content) -> WriteResult:
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)
        elif not isinstance(content, str):
            content = str(content)
        return await super().awrite(file_path, content)
```

Then pass it to `create_deep_agent`:

```python
backend = RobustFilesystemBackend(root_dir=str(_PROJECT_ROOT))

agent = create_deep_agent(
    model=_build_model(ORCHESTRATOR_MODEL),
    system_prompt=(...),
    skills=[f"{SKILLS_DIR}/"],
    backend=backend,
    subagents=[...],
)
```

**Imports to remove:** `from deepagents.middleware.filesystem import WriteFileSchema`, `from pydantic import field_validator`
**Code to remove:** The entire monkey-patch block (lines 59–102), the `_orig_write` reference, and the global module replacement.

### Fix 2: SubagentStatus.tsx — remove unused `isLoading`

```tsx
// Before:
export function SubagentStatus({ subagents, isLoading }: SubagentStatusProps) {

// After:
export function SubagentStatus({ subagents }: SubagentStatusProps) {
```

Keep `isLoading` in the `SubagentStatusProps` interface since callers may still pass it — just don't destructure it in the function signature if unused.

### Fix 2: useDeepAgent.ts — fix stream type mismatch

Cast through `any` for the assignment, since TypeScript can't express multiple overloads in a single function expression. The runtime behavior is correct — the patched function delegates to the original which handles overload dispatch internally.

```typescript
function createPatchedClient() {
  const client = new Client({ apiUrl: API_URL })
  const origStream = client.runs.stream.bind(client.runs)

  // Cast through `any` — we're intercepting all overloads and delegating
  // to the original, which handles overload dispatch at runtime.
  ;(client.runs as any).stream = function(
    threadId: any,
    assistantId: string,
    payload?: any,
  ) {
    if (payload?.streamMode) {
      const modes = Array.isArray(payload.streamMode)
        ? payload.streamMode
        : [payload.streamMode]
      const filtered = modes.filter((m: string) => SUPPORTED_STREAM_MODES.has(m))
      payload = {
        ...payload,
        streamMode: filtered.length > 0 ? filtered : ['values'],
      }
    }
    return origStream(threadId, assistantId, payload)
  }
  return client
}
```

Key changes:
- `(client.runs as any).stream = function(...)` instead of `client.runs.stream = (threadId: string, ...)`
- Parameters use `any` types since this is a runtime proxy
- Renamed `options` → `payload` to match the SDK's `RunsStreamPayload` naming
- `eslint-disable-next-line @typescript-eslint/no-explicit-any` comment preserved

---

## Step-by-Step Plan

### Step 1: Edit `src/agent.py`

1. Remove `from deepagents.middleware.filesystem import WriteFileSchema` (line 13)
2. Remove `from deepagents.backends.protocol import WriteResult` — keep this (used by subclass)
3. Remove the monkey-patch block (lines 59–102 entirely):
   - `_orig_write` assignment
   - `_patched_write` function
   - `FilesystemBackend.write = _patched_write`
   - `from pydantic import field_validator`
   - `_WriteFileSchema_original_fields` dict
   - `PatchedWriteFileSchema` class
   - `_fs_mod.WriteFileSchema = PatchedWriteFileSchema`
4. Add `RobustFilesystemBackend` class after `_build_model()` (uses `json` and `WriteResult` which are kept)
5. Instantiate `backend = RobustFilesystemBackend(root_dir=str(_PROJECT_ROOT))` before `create_deep_agent`
6. Add `backend=backend` parameter to `create_deep_agent()` call

### Step 2: Edit `frontend/src/components/SubagentStatus.tsx`

Remove `isLoading` from the destructuring at line 22 (keep it in the interface).

### Step 3: Edit `frontend/src/hooks/useDeepAgent.ts`

Rewrite `createPatchedClient()` with `any` casts for the overloaded method.

### Step 4: Verify — Python import

```bash
cd ~/development/deepagent-1 && uv run python -c "from src.agent import agent; print('OK:', type(agent).__name__)"
```

Expected: `OK: CompiledStateGraph`

### Step 5: Verify — TypeScript build

```bash
cd ~/development/deepagent-1/frontend && npm run build
```

Expected: exit code 0, no type errors

### Step 6: Commit

```bash
cd ~/development/deepagent-1
git add src/agent.py frontend/src/components/SubagentStatus.tsx frontend/src/hooks/useDeepAgent.ts
git commit -m "fix: replace monkey-patches with RobustFilesystemBackend subclass, fix TS build errors"
```

---

## Files Changing

| File | Change |
|------|--------|
| `src/agent.py` | Remove monkey-patches (lines 13, 59–102); add `RobustFilesystemBackend` subclass; pass `backend=` to `create_deep_agent` |
| `frontend/src/components/SubagentStatus.tsx` | Remove unused `isLoading` from destructuring |
| `frontend/src/hooks/useDeepAgent.ts` | Fix `client.runs.stream` type — cast through `any`, use `any` params |

---

## Risks & Tradeoffs

- **RobustFilesystemBackend**: If `deepagents` changes the `FilesystemBackend` constructor or `write`/`awrite` signatures in a future version, we may need to update the subclass. This is standard for subclass-based extension and far less fragile than the current monkey-patch approach. Pinning `deepagents>=0.4.8,<0.5.0` in `pyproject.toml` would prevent accidental breakage.
- **TypeScript `any` casts**: Necessary for the stream-mode patching pattern. TypeScript cannot express multiple call signatures in a single function expression. The `any` cast is scoped to the proxy function only and doesn't leak into the public API.
- **SubagentStatus `isLoading`**: Removed from destructuring but kept in the interface. If the component later needs `isLoading` for a spinner or disabled state, it can be added back trivially.

---

## Open Questions

- Pin `deepagents>=0.4.8,<0.5.0` in `pyproject.toml`? (Recommended but out of scope for this fix)
- Merge `feature/fe-harness` → `main` after this fix? (Process decision, not covered here)