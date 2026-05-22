# Top 5 Refactorings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply five high-leverage refactorings that consolidate duplicated logic, restore type safety, and fix one UX bug — without changing observable behavior of the agent or chat UI.

**Architecture:** Pure refactorings. Changes split across the Python agent (`src/agent.py`) and the React chat frontend (`frontend/src/`). Order is dependency-aware: shared frontend types land first so later tasks can consume them, frontend type-augmentation lands second to remove `as any` casts, then a single-component shared lib for tool helpers, then a UX bug fix, then the highest-risk Python work last so it's bisectable.

**Tech Stack:** Python 3.11+ / `deepagents>=0.4.8` / `langchain-ollama` / Pydantic v2 (backend); React 19 / TypeScript (strict) / Vite / Tailwind / `@langchain/react` / `@langchain/langgraph-sdk` (frontend).

**Branch:** `refactor/top-5-refactorings` (worktree at `.worktrees/refactor-top-5/`)

**Baseline (must keep passing):**
- `uv run python -c "from src.agent import agent; print('OK')"` → prints `OK`
- `cd frontend && npm run build` → builds clean (warnings about chunk size are pre-existing and OK)

---

## File Structure

**Created:**
- `frontend/src/types/messages.ts` — discriminated-union `Message` type and `is*Message` predicates (Task 1)
- `frontend/src/types/langgraph-augment.d.ts` — module augmentation for `@langchain/react` (Task 3)
- `frontend/src/lib/tools.ts` — centralized tool-call icon + description helpers (Task 2)

**Modified:**
- `frontend/src/hooks/useDeepAgent.ts` — consume new Message types, drop `as any` casts via augmentation (Tasks 1, 3)
- `frontend/src/components/ChatMessage.tsx` — consume Message types + predicates, import tool helpers (Tasks 1, 2)
- `frontend/src/components/SubagentStatus.tsx` — import tool helpers from shared lib (Task 2)
- `frontend/src/App.tsx` — use `isAIMessage` predicate, fix auto-scroll (Tasks 1, 4)
- `src/agent.py` — collapse three-layer `write_file` dict-coercion stack into single Pydantic schema, strip prompt warning (Task 5)

**Deleted (in Task 5):**
- `RobustFilesystemBackend` class (dead defense layer once Pydantic schema intercepts)
- "CRITICAL: Tool Call Format" block in `REACT_DEV_SYSTEM_PROMPT`

---

## Dependency Order

```
Task 1 (Message types) ──┬──> Task 2 (tool helpers, uses Message type indirectly)
                         └──> Task 3 (langgraph augmentation, uses SubagentInfo)
Task 4 (auto-scroll) ──── independent
Task 5 (write_file stack) ──── independent (last for bisectability)
```

---

## Task 1: Centralize frontend Message type + predicates

**Files:**
- Create: `frontend/src/types/messages.ts`
- Modify: `frontend/src/hooks/useDeepAgent.ts` (replace inline message types lines 6-24 and 100-108)
- Modify: `frontend/src/components/ChatMessage.tsx` (replace inline message type lines 4-13, replace string-comparison checks lines 45-46)
- Modify: `frontend/src/App.tsx` (replace inline message-kind check at line 66)

**Context:** Today the same "what is a chat message" shape is redeclared in three files with subtle differences (one has `role`, one doesn't; tool detection uses two different string literals: `'tool'` and `'ToolMessage'`). Centralize into a discriminated union with predicate functions so future contributors edit one file when LangChain adds a new message type.

- [ ] **Step 1: Create the shared types file**

Create `frontend/src/types/messages.ts`:

```ts
export type ContentBlock = { type: string; text?: string }
export type MessageContent = string | ContentBlock[]

export interface BaseMessage {
  id?: string
  content: MessageContent
  name?: string
  additional_kwargs?: Record<string, unknown>
}

export interface HumanMessage extends BaseMessage {
  type: 'human'
  role?: 'user'
}

export interface ToolMessage extends BaseMessage {
  type: 'tool' | 'ToolMessage'
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
  id: string
}

export interface AIMessage extends BaseMessage {
  type?: string
  role?: string
  tool_calls?: ToolCall[]
}

export type Message = HumanMessage | ToolMessage | AIMessage

export const isHumanMessage = (m: Message): m is HumanMessage =>
  m.type === 'human' || (m as HumanMessage).role === 'user'

export const isToolMessage = (m: Message): m is ToolMessage =>
  m.type === 'tool' || m.type === 'ToolMessage'

export const isAIMessage = (m: Message): m is AIMessage =>
  !isHumanMessage(m) && !isToolMessage(m)

export function extractText(content: MessageContent): string {
  if (typeof content === 'string') return content
  return content
    .filter((b) => b.type === 'text' && b.text)
    .map((b) => b.text!)
    .join('\n')
}
```

- [ ] **Step 2: Verify the new file type-checks in isolation**

Run: `cd frontend && npx tsc --noEmit src/types/messages.ts`
Expected: No output (success). If errors about `verbatimModuleSyntax` or similar appear, re-export types using `export type { ... }` syntax — the project uses TS strict mode.

- [ ] **Step 3: Update `useDeepAgent.ts` to consume Message types**

In `frontend/src/hooks/useDeepAgent.ts`, replace lines 1-3 and the `DeepAgentState` interface (lines 5-24) with:

```ts
import { useMemo } from 'react'
import { useStream } from '@langchain/react'
import { Client } from '@langchain/langgraph-sdk'
import type { Message } from '../types/messages'

interface DeepAgentState {
  messages: Message[]
  todos?: Array<{
    id: string
    content: string
    status: string
  }>
}
```

Then in the same file, replace the inline message-typed return (lines 100-108) with:

```ts
    messages: (stream.messages ?? []) as Message[],
```

- [ ] **Step 4: Update `ChatMessage.tsx` to use the shared type and predicates**

In `frontend/src/components/ChatMessage.tsx`, replace the file's contents top-to-`extractContent` helper (lines 1-22) with:

```tsx
import { Bot, User, Wrench, Loader2 } from 'lucide-react'
import type { Message } from '../types/messages'
import { isHumanMessage, isToolMessage, extractText } from '../types/messages'

export interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
}
```

Then replace the `extractContent` call sites in the same file (find every `extractContent(message.content)` — there is one at line 47) with `extractText(message.content)`.

Then replace the type-detection lines (lines 45-46):

```tsx
  const isHuman = message.type === 'human' || message.role === 'user'
  const isTool = message.type === 'tool' || message.type === 'ToolMessage'
```

with:

```tsx
  const isHuman = isHumanMessage(message)
  const isTool = isToolMessage(message)
```

The rest of the file stays as-is — `message.tool_calls` is now properly typed via `AIMessage`.

- [ ] **Step 5: Update `App.tsx` to use the AI-message predicate**

In `frontend/src/App.tsx`, add to the imports at the top of the file:

```tsx
import { isAIMessage } from './types/messages'
```

Then replace line 66:

```tsx
  const lastAiMsg = [...messages].reverse().find(m => m.type !== 'human' && m.type !== 'tool' && m.type !== 'ToolMessage')
```

with:

```tsx
  const lastAiMsg = [...messages].reverse().find(isAIMessage)
```

- [ ] **Step 6: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No errors.

If the build complains about `additional_kwargs` typing or `tool_calls` typing on the `AIMessage`, double-check that `ChatMessage.tsx` no longer redeclares the message shape locally — the file should import the type, not redefine it.

- [ ] **Step 7: Build the frontend end-to-end**

Run: `cd frontend && npm run build`
Expected: Build succeeds (chunk-size warning is pre-existing and OK).

- [ ] **Step 8: Verify agent still imports**

Run: `uv run python -c "from src.agent import agent; print('OK')"`
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add frontend/src/types/messages.ts \
        frontend/src/hooks/useDeepAgent.ts \
        frontend/src/components/ChatMessage.tsx \
        frontend/src/App.tsx
git commit -m "refactor(fe): centralize Message type and predicates

Three near-duplicate inline message types collapsed into one
discriminated union in types/messages.ts with isHumanMessage /
isToolMessage / isAIMessage predicates. Consumers now share one
source of truth for what counts as each message kind."
```

---

## Task 2: Centralize tool-call icon and description helpers

**Files:**
- Create: `frontend/src/lib/tools.ts`
- Modify: `frontend/src/components/SubagentStatus.tsx` (remove inline `getToolIcon` lines 16-20, import from lib)
- Modify: `frontend/src/components/ChatMessage.tsx` (remove inline `formatToolName` lines 24-26 and `getToolDescription` lines 28-42, import from lib)

**Context:** Tool reasoning is split: `SubagentStatus.tsx` knows tool icons, `ChatMessage.tsx` knows tool descriptions. Both reason about the same tool taxonomy (`task`, `write_file`, `execute`, `read_file`). There is also a latent bug: `getToolDescription` for `write_file` reads `args.path`, but the actual tool argument name is `file_path` (see `_PatchedWriteFileSchema.file_path` in `src/agent.py:103`). Centralize and fix the bug.

- [ ] **Step 1: Create the shared tools lib**

Create `frontend/src/lib/tools.ts`:

```ts
import { FileText, Terminal, Wrench, type LucideIcon } from 'lucide-react'

interface ToolEntry {
  icon: LucideIcon
  describe: (args: Record<string, unknown>) => string
}

const filePathOf = (args: Record<string, unknown>): string =>
  String(args.file_path ?? args.path ?? 'file')

const TOOL_REGISTRY: Record<string, ToolEntry> = {
  task: {
    icon: Wrench,
    describe: (args) =>
      String(args.subagent_type ?? args.task ?? 'Running subagent...'),
  },
  write_file: {
    icon: FileText,
    describe: (args) => `Writing ${filePathOf(args)}`,
  },
  read_file: {
    icon: FileText,
    describe: (args) => `Reading ${filePathOf(args)}`,
  },
  execute: {
    icon: Terminal,
    describe: (args) => `Running: ${String(args.command ?? 'command')}`,
  },
}

export function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function getToolIcon(name: string | undefined): LucideIcon {
  if (!name) return Wrench
  const entry = TOOL_REGISTRY[name]
  if (entry) return entry.icon
  if (name.includes('file') || name.includes('write')) return FileText
  if (name.includes('execute') || name.includes('command')) return Terminal
  return Wrench
}

export function getToolDescription(
  name: string,
  args: Record<string, unknown>,
): string {
  const entry = TOOL_REGISTRY[name]
  if (entry) return entry.describe(args)
  return formatToolName(name)
}
```

- [ ] **Step 2: Type-check the new lib in isolation**

Run: `cd frontend && npx tsc --noEmit src/lib/tools.ts`
Expected: No errors.

- [ ] **Step 3: Update `SubagentStatus.tsx` to use the shared lib**

In `frontend/src/components/SubagentStatus.tsx`:

Replace the imports at line 1:

```tsx
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'
import type { SubagentInfo } from '../hooks/useDeepAgent'
import { getToolIcon } from '../lib/tools'
```

Delete the inline `getToolIcon` function (lines 16-20 in the original file):

```tsx
function getToolIcon(name: string) {
  if (name?.includes('file') || name?.includes('write')) return FileText
  if (name?.includes('execute') || name?.includes('command')) return Terminal
  return Wrench
}
```

The `Wrench`, `FileText`, `Terminal` lucide imports are now unused inside `SubagentStatus.tsx` and can be dropped (already done in the import-replacement above). The body of the component is unchanged — it already calls `getToolIcon(toolName ?? '')`.

- [ ] **Step 4: Update `ChatMessage.tsx` to use the shared lib**

In `frontend/src/components/ChatMessage.tsx`:

Add to the existing imports (after the `isHumanMessage` import added in Task 1):

```tsx
import { getToolDescription } from '../lib/tools'
```

Delete the inline `formatToolName` (lines 24-26 in the original) and `getToolDescription` (lines 28-42 in the original):

```tsx
function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function getToolDescription(tc: { name: string; args: Record<string, unknown> }): string {
  // ...switch statement...
}
```

In the JSX, change the call site (was `getToolDescription(tc)`) to:

```tsx
                  <span className="font-medium">{getToolDescription(tc.name, tc.args)}</span>
```

- [ ] **Step 5: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No errors.

If the build complains about unused imports in `SubagentStatus.tsx`, double-check that the `lucide-react` import line was replaced (not appended).

- [ ] **Step 6: Build the frontend end-to-end**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 7: Visually confirm the file_path fix lands**

Run: `grep -n "file_path" frontend/src/lib/tools.ts`
Expected: One match for `args.file_path ?? args.path` in `filePathOf`. This proves the latent `path` vs `file_path` bug is now handled.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/tools.ts \
        frontend/src/components/SubagentStatus.tsx \
        frontend/src/components/ChatMessage.tsx
git commit -m "refactor(fe): centralize tool-call icon + description helpers

Tool reasoning was split across SubagentStatus and ChatMessage with
duplicated taxonomy. Consolidated into lib/tools.ts. Also fixes a
latent bug where write_file/read_file descriptions read args.path
when the actual tool arg is file_path (per _PatchedWriteFileSchema)."
```

---

## Task 3: Drop `as any` casts via module augmentation of `@langchain/react`

**Files:**
- Create: `frontend/src/types/langgraph-augment.d.ts`
- Modify: `frontend/src/hooks/useDeepAgent.ts` (drop `as any` casts on lines 79-85 and 95)

**Context:** `useDeepAgent.ts` uses three escape hatches because `@langchain/react` and `@langchain/langgraph-sdk` don't yet expose the surface this app needs at the type level. The runtime works; the types lie. Fix with module augmentation so the casts go away.

The Client.runs.stream patch (the `createPatchedClient` factory at lines 48-73) is a separate concern — its `as any` is harder to remove cleanly without breaking the overload-dispatch behavior. **This task does NOT touch that factory.** It only addresses the `useStream` options cast and the `subagents` field cast.

- [ ] **Step 1: Verify both casts exist in the current code**

Run: `grep -n "as any\|as Record<string, unknown>" frontend/src/hooks/useDeepAgent.ts`
Expected: At least three matches — the patched-client cast, the `useStream` options cast, and the `subagents` cast.

- [ ] **Step 2: Create the augmentation file**

Create `frontend/src/types/langgraph-augment.d.ts`:

```ts
import '@langchain/react'
import type { SubagentInfo } from '../hooks/useDeepAgent'

declare module '@langchain/react' {
  interface UseStreamOptions<_StateType, _UpdateType, _CustomEventType> {
    fetchStateHistory?: boolean
    filterSubagentMessages?: boolean
  }

  interface UseStream<_StateType, _UpdateType, _CustomEventType> {
    subagents?: Map<string, SubagentInfo>
  }
}
```

NOTE on the interface names and generic counts: `@langchain/react` exports `UseStreamOptions` and the hook returns a typed result. The exact interface names and generic arity may differ between SDK versions. If TypeScript reports `Cannot augment ...` errors, run `cat node_modules/@langchain/react/dist/index.d.ts | head -200` to find the actual exported interface names, then adjust this file accordingly. The augmentation pattern is what matters — don't fight the SDK's specific naming.

- [ ] **Step 3: Type-check the augmentation file is picked up**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: Either passes (great), or fails with a clear error about the augmentation. If it fails, follow the note in Step 2 to find the right interface names.

- [ ] **Step 4: Drop the `useStream` options cast**

In `frontend/src/hooks/useDeepAgent.ts`, replace lines 78-85:

```ts
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stream = useStream<DeepAgentState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
    client,
    fetchStateHistory: true,
    filterSubagentMessages: true,
  } as any)
```

with:

```ts
  const stream = useStream<DeepAgentState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
    client,
    fetchStateHistory: true,
    filterSubagentMessages: true,
  })
```

- [ ] **Step 5: Drop the `subagents` cast**

In `frontend/src/hooks/useDeepAgent.ts`, replace line 94-95:

```ts
  // Extract subagents from the stream (available at runtime even if not in BaseStream type)
  const subagents = (stream as Record<string, unknown>).subagents as Map<string, SubagentInfo> | undefined
```

with:

```ts
  const subagents = stream.subagents
```

- [ ] **Step 6: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No errors. If `stream.subagents` is reported as `unknown`, the augmentation interface name is wrong — see Step 2 note.

- [ ] **Step 7: Build the frontend end-to-end**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 8: Confirm no eslint-disable lines remain for the dropped casts**

Run: `grep -n "no-explicit-any" frontend/src/hooks/useDeepAgent.ts`
Expected: At most ONE match (the `client.runs as any` patch in `createPatchedClient`, which this task explicitly leaves alone). If two matches remain, the `useStream` cast wasn't fully removed.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/types/langgraph-augment.d.ts \
        frontend/src/hooks/useDeepAgent.ts
git commit -m "refactor(fe): drop as-any casts via module augmentation

Two of the three as-any escape hatches in useDeepAgent.ts came from
@langchain/react not exposing fetchStateHistory, filterSubagentMessages,
or stream.subagents in its public types. Augmented the module so those
fields are typed; removed the runtime-cast laundering. The
createPatchedClient stream-mode patch is unchanged — its overload
intercept needs deeper SDK work."
```

---

## Task 4: Auto-scroll only when user is near the bottom

**Files:**
- Modify: `frontend/src/App.tsx` (the `useEffect` at lines 61-63 and the messages container at line 99)

**Context:** Today every new message yanks the viewport to the bottom, even when the user has scrolled up to read history. For a streaming agent that emits dozens of messages per run, this is a real UX bug. Fix: only auto-scroll when the user is already within 80px of the bottom — the standard "auto-follow if you're already following" pattern used by ChatGPT, Claude.ai, and `tail -f` viewers.

- [ ] **Step 1: Add container ref and follow-state in `AppContent`**

In `frontend/src/App.tsx`, the `AppContent` function currently starts (around line 56):

```tsx
function AppContent() {
  const { messages, isLoading, subagents, sendMessage, error } = useDeepAgent()
  const errorMessage = error ? (error instanceof Error ? error.message : String(error)) : null
  const bottomRef = useRef<HTMLDivElement>(null)
```

Add the import for `useState` at the top of the file (modify the existing react import):

```tsx
import { Component, type ReactNode, useRef, useEffect, useState } from 'react'
```

Then replace the body of `AppContent` from `bottomRef` through the existing `useEffect` (lines 59-67) with:

```tsx
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoFollow, setAutoFollow] = useState(true)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      setAutoFollow(distanceFromBottom < 80)
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (autoFollow) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, autoFollow])

  // Find the last AI message that might still be streaming
  const lastAiMsg = [...messages].reverse().find(isAIMessage)
  const streamingId = isLoading ? lastAiMsg?.id : undefined
```

(The `lastAiMsg` line was added in Task 1 — leave it as-is, just shown here for context.)

- [ ] **Step 2: Attach `containerRef` to the messages-scroll container**

In `frontend/src/App.tsx`, the messages container is currently (line 99):

```tsx
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
```

Replace with:

```tsx
      {/* Messages */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-6">
```

- [ ] **Step 3: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No errors.

- [ ] **Step 4: Build the frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Manual UX verification (sanity)**

Verification commands (with both servers running):

Terminal 1: `cd /Users/scottwilliams/development/deepagent-1/.worktrees/refactor-top-5 && uv run langgraph dev`

Terminal 2: `cd /Users/scottwilliams/development/deepagent-1/.worktrees/refactor-top-5/frontend && npm run dev`

Then:
1. Open `http://localhost:5173`
2. Send: "Build me a simple counter app"
3. As messages stream in, scroll to the top of the chat — confirm the viewport stays at the top (does NOT auto-scroll).
4. Scroll back to within ~80px of the bottom — confirm auto-scroll resumes.

If you cannot run the servers (e.g. no Ollama access), this verification is **skipped** and the type-check + build is the gate. Note the skip in the commit body if so.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix(fe): auto-scroll only when user is near the bottom

Previously every message update scrolled the viewport to the bottom,
yanking the user away when they scrolled up to read history. Now
tracks distance-from-bottom on scroll and only auto-follows when the
user is within 80px of the bottom — standard streaming-chat pattern."
```

---

## Task 5: Collapse the `write_file` dict-coercion stack in `src/agent.py`

**Files:**
- Modify: `src/agent.py` (delete `RobustFilesystemBackend` class lines 76-90; strip the "CRITICAL: Tool Call Format" prompt block lines 38-50; switch the `backend` instance at line 131 to plain `FilesystemBackend`)

**Context:** Today `src/agent.py` has FOUR overlapping defenses for one bug (GLM passing dicts as `write_file` content):
1. `_coerce_to_str` helper — keep, it's the primitive
2. `RobustFilesystemBackend` — DELETE, it's dead code (Pydantic schema runs first, backend never sees a dict)
3. `_PatchedWriteFileSchema` — keep, this is the real fix at the boundary
4. Class-level monkey-patch on `FilesystemMiddleware._create_write_file_tool` — keep, required to install the schema (the comment at lines 114-119 explains why)
5. "CRITICAL: Tool Call Format" prompt block in `REACT_DEV_SYSTEM_PROMPT` — DELETE, schema handles it; saves prompt tokens per run

The recent commit log (`refactor: fix broken import, eliminate DRY violation`, `fix: replace monkey-patches with RobustFilesystemBackend subclass`) shows this area has churned 3+ times — collapsing the dead layers stops the churn.

This task is last because it's the highest-risk: it touches the agent boundary and the system prompt for the React-developer subagent.

- [ ] **Step 1: Capture pre-refactor behavior in a one-liner**

Run:

```bash
uv run python -c "
from src.agent import _PatchedWriteFileSchema
s = _PatchedWriteFileSchema(file_path='/x', content={'a': 1, 'b': [2, 3]})
assert isinstance(s.content, str), f'expected str, got {type(s.content).__name__}'
assert '\"a\": 1' in s.content, f'expected JSON serialization, got: {s.content!r}'
print('PRE_REFACTOR_OK')
"
```

Expected: `PRE_REFACTOR_OK`. This proves the dict-coercion behavior we must preserve.

- [ ] **Step 2: Delete the `RobustFilesystemBackend` class**

In `src/agent.py`, delete lines 76-90 (the entire class plus its docstring and the blank line before it):

```python


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
```

- [ ] **Step 3: Drop the unused `WriteResult` import**

In `src/agent.py`, the import at line 13 was only used by `RobustFilesystemBackend`. Delete:

```python
from deepagents.backends.protocol import WriteResult
```

- [ ] **Step 4: Switch backend instantiation to plain `FilesystemBackend`**

In `src/agent.py`, line 131 currently reads:

```python
backend = RobustFilesystemBackend(root_dir=str(_PROJECT_ROOT))
```

Replace with:

```python
backend = FilesystemBackend(root_dir=str(_PROJECT_ROOT))
```

- [ ] **Step 5: Strip the "CRITICAL: Tool Call Format" prompt block**

In `src/agent.py`, the `REACT_DEV_SYSTEM_PROMPT` constant currently spans lines 25-50. Delete the block from `## CRITICAL: Tool Call Format` through the blank line before `## Design Principles`. After this edit, the prompt should read (verbatim, including triple-quote bounds):

```python
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

## Design Principles
- Use Tailwind CSS utility classes
- Mobile-responsive by default
- Realistic mock data (not lorem ipsum)
- Working interactions (button clicks, form inputs, toggles)
- Clean component decomposition
- NEVER leave placeholder content
"""
```

- [ ] **Step 6: Verify post-refactor behavior matches pre-refactor**

Run the same one-liner from Step 1:

```bash
uv run python -c "
from src.agent import _PatchedWriteFileSchema
s = _PatchedWriteFileSchema(file_path='/x', content={'a': 1, 'b': [2, 3]})
assert isinstance(s.content, str), f'expected str, got {type(s.content).__name__}'
assert '\"a\": 1' in s.content, f'expected JSON serialization, got: {s.content!r}'
print('POST_REFACTOR_OK')
"
```

Expected: `POST_REFACTOR_OK`. This proves the schema-level coercion still works after the dead layers are removed.

- [ ] **Step 7: Verify the agent still imports**

Run:

```bash
uv run python -c "from src.agent import agent; print('OK')"
```

Expected: `OK`.

- [ ] **Step 8: Verify the unused name is gone**

Run:

```bash
grep -n "RobustFilesystemBackend\|WriteResult" src/agent.py
```

Expected: No matches (zero output). If any match remains, the deletion in Steps 2/3 was incomplete.

- [ ] **Step 9: Verify the prompt warning is gone**

Run:

```bash
grep -n "CRITICAL: Tool Call Format\|MUST be a plain string" src/agent.py
```

Expected: No matches (zero output).

- [ ] **Step 10: Commit**

```bash
git add src/agent.py
git commit -m "refactor: collapse write_file dict-coercion stack to one layer

The Pydantic schema (_PatchedWriteFileSchema) coerces dict content
to a JSON string at the tool-args boundary, so the backend never
sees a dict. RobustFilesystemBackend was dead defense-in-depth;
removed. The CRITICAL: Tool Call Format prompt block was also
redundant — schema handles it — and was burning tokens per run.
The class-level monkey-patch and _PatchedWriteFileSchema stay;
they are the actual fix."
```

---

## Self-Review Checklist (run by controller before dispatching subagents)

**Spec coverage:**
- [x] #1 (write_file stack collapse) → Task 5
- [x] #2 (Message type) → Task 1
- [x] #3 (`as any` removal) → Task 3
- [x] #4 (tool helpers) → Task 2
- [x] #5 (auto-scroll) → Task 4

**Type consistency:**
- `Message` exported from `frontend/src/types/messages.ts` is consumed by `useDeepAgent.ts`, `ChatMessage.tsx`, `App.tsx` — same name, same shape.
- `extractText` (Task 1) replaces local `extractContent` (was in `ChatMessage.tsx`) — Task 1 Step 4 explicitly updates the call site.
- `getToolDescription(name, args)` signature in `lib/tools.ts` (Task 2) takes two args; the call site in `ChatMessage.tsx` was `getToolDescription(tc)` (one arg) — Task 2 Step 4 explicitly updates the call site to `getToolDescription(tc.name, tc.args)`.
- `getToolIcon(name | undefined)` accepts undefined; existing call site in `SubagentStatus.tsx` passes `toolName ?? ''` so passing a string still works.
- `isAIMessage` predicate is used in both Task 1 (App.tsx line 66 replacement) and Task 4 (still referenced in the streaming-id block) — Task 4 leaves that line unchanged.

**No-placeholder scan:** No "TBD", "implement appropriate", or "similar to" placeholders. Every code step shows the code.

**Risk gradient:** Tasks 1-4 are pure frontend with type-check + build as gates. Task 5 has explicit before/after behavior verification (Steps 1 and 6).

---

## Execution

Plan complete. Recommended execution: **Subagent-Driven** (skill `superpowers:subagent-driven-development`) — fresh subagent per task with two-stage review, all in this session.
