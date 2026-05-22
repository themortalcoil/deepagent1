import { Loader2, CheckCircle2, XCircle, Clock, Wrench, FileText, Terminal } from 'lucide-react'
import type { SubagentInfo } from '../hooks/useDeepAgent'

interface SubagentStatusProps {
  subagents: Map<string, SubagentInfo>
  isLoading?: boolean
}

const statusConfig = {
  pending: { icon: Clock, label: 'Queued', color: 'text-gray-500 bg-gray-50 border-gray-200' },
  running: { icon: Loader2, label: 'Working', color: 'text-blue-600 bg-blue-50 border-blue-200' },
  complete: { icon: CheckCircle2, label: 'Done', color: 'text-green-600 bg-green-50 border-green-200' },
  error: { icon: XCircle, label: 'Error', color: 'text-red-600 bg-red-50 border-red-200' },
} as const

function getToolIcon(name: string) {
  if (name?.includes('file') || name?.includes('write')) return FileText
  if (name?.includes('execute') || name?.includes('command')) return Terminal
  return Wrench
}

export function SubagentStatus({ subagents }: SubagentStatusProps) {
  if (subagents.size === 0) return null

  const entries = Array.from(subagents.entries())

  return (
    <div className="border-b border-gray-200 bg-white px-4 py-2">
      <div className="mx-auto max-w-3xl space-y-1.5">
        {entries.map(([name, info]) => {
          const status = info.status as keyof typeof statusConfig
          const config = statusConfig[status] ?? statusConfig.pending
          const Icon = config.icon
          const toolName = info.toolCall?.name
          const ToolIcon = getToolIcon(toolName ?? '')
          const taskDesc = String(info.toolCall?.args?.task ?? info.toolCall?.args?.subagent_type ?? name)

          // Get last meaningful message from subagent
          const lastMsg = info.messages?.filter(m => m.content && (typeof m.content === 'string' ? m.content.trim() : true)).at(-1)
          const lastContent = lastMsg
            ? (typeof lastMsg.content === 'string' ? lastMsg.content : lastMsg.content.filter(b => b.type === 'text').map(b => b.text).join(' '))
            : null

          return (
            <div key={name} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${config.color}`}>
              <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${info.status === 'running' ? 'animate-spin' : ''}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{taskDesc}</span>
                  <span className="text-xs opacity-60">{config.label}</span>
                  {toolName && (
                    <span className="inline-flex items-center gap-0.5 rounded bg-white/60 px-1.5 py-0.5 text-xs font-mono">
                      <ToolIcon className="h-2.5 w-2.5" />
                      {toolName}
                    </span>
                  )}
                </div>
                {lastContent && (
                  <p className="mt-1 text-xs opacity-70 truncate">{lastContent.slice(0, 200)}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}