import { Loader2, CheckCircle2, XCircle, Clock, Wrench } from 'lucide-react'
import type { SubagentInfo } from '../hooks/useDeepAgent'

interface SubagentStatusProps {
  subagents: Map<string, SubagentInfo> | undefined
}

const statusConfig = {
  pending: { icon: Clock, label: 'Waiting', color: 'text-gray-500 bg-gray-50' },
  running: { icon: Loader2, label: 'Working', color: 'text-blue-600 bg-blue-50' },
  complete: { icon: CheckCircle2, label: 'Done', color: 'text-green-600 bg-green-50' },
  error: { icon: XCircle, label: 'Error', color: 'text-red-600 bg-red-50' },
} as const

export function SubagentStatus({ subagents }: SubagentStatusProps) {
  if (!subagents || subagents.size === 0) return null

  const entries = Array.from(subagents.entries())

  return (
    <div className="space-y-2 px-4">
      {entries.map(([name, info]) => {
        const status = info.status as keyof typeof statusConfig
        const config = statusConfig[status] ?? statusConfig.pending
        const Icon = config.icon
        const toolName = info.toolCall?.name

        return (
          <div key={name} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${config.color}`}>
            <Icon className={`h-4 w-4 shrink-0 ${info.status === 'running' ? 'animate-spin' : ''}`} />
            <span className="font-medium">{String(info.toolCall?.args?.subagent_type ?? name)}</span>
            <span className="text-xs opacity-70">{config.label}</span>
            {toolName && (
              <div className="ml-auto flex gap-1">
                <span className="inline-flex items-center gap-0.5 rounded bg-white/60 px-1.5 py-0.5 text-xs font-mono">
                  <Wrench className="h-2.5 w-2.5" />
                  {toolName}
                </span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}