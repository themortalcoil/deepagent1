import { Bot, User, Wrench, Loader2 } from 'lucide-react'
import type { Message } from '../types/messages'
import { isHumanMessage, isToolMessage, extractText } from '../types/messages'

export interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function getToolDescription(tc: { name: string; args: Record<string, unknown> }): string {
  const args = tc.args
  switch (tc.name) {
    case 'task':
      return String(args.subagent_type ?? args.task ?? 'Running subagent...')
    case 'write_file':
      return `Writing ${String(args.path ?? 'file')}`
    case 'execute':
      return `Running: ${String(args.command ?? 'command')}`
    case 'read_file':
      return `Reading ${String(args.path ?? 'file')}`
    default:
      return formatToolName(tc.name)
  }
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isHuman = isHumanMessage(message)
  const isTool = isToolMessage(message)
  const text = extractText(message.content)
  const hasContent = text.length > 0

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

  // AI message — show tool calls as progress steps
  const toolCalls = message.tool_calls ?? []
  const showToolProgress = toolCalls.length > 0

  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-600">
        <Bot className="h-4 w-4" />
      </div>
      <div className="max-w-[80%] space-y-2">
        {hasContent && (
          <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-sm text-gray-800 shadow-sm border border-gray-100">
            <div className="prose prose-sm max-w-none whitespace-pre-wrap">
              {text}
              {isStreaming && <span className="inline-block w-1.5 h-4 ml-0.5 bg-blue-500 animate-pulse rounded-sm align-text-bottom" />}
            </div>
          </div>
        )}
        {showToolProgress && (
          <div className="space-y-1">
            {toolCalls.map((tc, i) => {
              const isLast = i === toolCalls.length - 1
              const isRunning = isLast && isStreaming
              return (
                <div
                  key={tc.id}
                  className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs ${
                    isRunning
                      ? 'bg-blue-50 border border-blue-200 text-blue-700'
                      : 'bg-gray-50 border border-gray-200 text-gray-600'
                  }`}
                >
                  {isRunning ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Wrench className="h-3 w-3" />
                  )}
                  <span className="font-medium">{getToolDescription(tc)}</span>
                </div>
              )
            })}
          </div>
        )}
        {!hasContent && !showToolProgress && isStreaming && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
      </div>
    </div>
  )
}