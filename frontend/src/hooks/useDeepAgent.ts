import { useStream } from '@langchain/react'

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

export function useDeepAgent() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stream = useStream<DeepAgentState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
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