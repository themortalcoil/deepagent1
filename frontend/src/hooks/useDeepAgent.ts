import { useStream } from '@langchain/react'

const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL || 'http://127.0.0.1:2024'
const ASSISTANT_ID = import.meta.env.VITE_ASSISTANT_ID || 'deepagent'

export function useDeepAgent() {
  const stream = useStream({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
  })

  const sendMessage = (content: string) => {
    stream.submit(
      { messages: [{ content, type: 'human' }] },
      { streamSubgraphs: true },
    )
  }

  return {
    stream,
    sendMessage,
  }
}