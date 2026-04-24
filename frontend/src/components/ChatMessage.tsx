import { Bot, User, Wrench } from 'lucide-react'

export interface ChatMessageProps {
  message: {
    type?: string
    role?: string
    content: string | Array<{ type: string; text?: string }>
    name?: string
    id?: string
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