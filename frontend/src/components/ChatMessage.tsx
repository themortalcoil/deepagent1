import { Bot, User, Wrench } from 'lucide-react'
import type { BaseMessage } from '@langchain/core/messages'

interface ChatMessageProps {
  message: BaseMessage
}

function extractContent(content: unknown): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .filter((block: any) => block.type === 'text' && block.text)
      .map((block: any) => block.text)
      .join('\n')
  }
  return String(content)
}

export function ChatMessage({ message }: ChatMessageProps) {
  const msgType = message._getType()
  const text = extractContent(message.content)
  const isHuman = msgType === 'human'
  const isTool = msgType === 'tool'

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
  const toolCalls = (message as any).tool_calls as Array<{ name: string; args: Record<string, unknown>; id: string }> | undefined

  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-600">
        <Bot className="h-4 w-4" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-sm text-gray-800 shadow-sm border border-gray-100">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">{text}</div>
        {toolCalls && toolCalls.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {toolCalls.map((tc) => (
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