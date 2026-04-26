import { useMemo } from 'react'
import { useStream } from '@langchain/react'
import { Client } from '@langchain/langgraph-sdk'

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

/** Subagent stream info returned by the hook */
export interface SubagentInfo {
  id: string
  status: 'pending' | 'running' | 'complete' | 'error'
  messages: Array<{ content: string | Array<{ type: string; text?: string }>; type?: string }>
  toolCall?: { name: string; args: Record<string, unknown>; id: string }
  result: string | null
}

const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL || 'http://127.0.0.1:2024'
const ASSISTANT_ID = import.meta.env.VITE_ASSISTANT_ID || 'deepagent'

/** Stream modes supported by the langgraph-cli dev server (0.4.x) */
const SUPPORTED_STREAM_MODES = new Set([
  'values', 'messages', 'messages-tuple', 'updates',
  'events', 'debug', 'custom',
])

/**
 * Create a patched Client that filters out unsupported stream modes
 * (e.g. "tools" which isn't in the langgraph-cli 0.4.x enum).
 */
function createPatchedClient() {
  const client = new Client({ apiUrl: API_URL })
  const origStream = client.runs.stream.bind(client.runs)

  // Cast through `any` — we're intercepting all overloads and delegating
  // to the original, which handles overload dispatch at runtime.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

export function useDeepAgent() {
  const client = useMemo(() => createPatchedClient(), [])

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stream = useStream<DeepAgentState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
    client,
    fetchStateHistory: true,
    filterSubagentMessages: true,
  } as any)

  const sendMessage = (content: string) => {
    stream.submit(
      { messages: [{ content, type: 'human' }] },
      { streamSubgraphs: true },
    )
  }

  // Extract subagents from the stream (available at runtime even if not in BaseStream type)
  const subagents = (stream as Record<string, unknown>).subagents as Map<string, SubagentInfo> | undefined

  return {
    ...stream,
    sendMessage,
    messages: (stream.messages ?? []) as Array<{
      type?: string
      role?: string
      content: string | Array<{ type: string; text?: string }>
      name?: string
      id?: string
      tool_calls?: Array<{ name: string; args: Record<string, unknown>; id: string }>
      additional_kwargs?: Record<string, unknown>
    }>,
    isLoading: stream.isLoading,
    error: stream.error,
    subagents: subagents ?? new Map<string, SubagentInfo>(),
  }
}

export type { DeepAgentState }