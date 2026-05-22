import { Component, type ReactNode, useRef, useEffect } from 'react'
import { Bot } from 'lucide-react'
import { useDeepAgent } from './hooks/useDeepAgent'
import { ChatMessage } from './components/ChatMessage'
import { ChatInput } from './components/ChatInput'
import { SubagentStatus } from './components/SubagentStatus'
import { isAIMessage } from './types/messages'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-gray-50 p-8">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900">Something went wrong</h2>
            <p className="mt-2 text-sm text-gray-500">{this.state.error?.message}</p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  )
}

function AppContent() {
  const { messages, isLoading, subagents, sendMessage, error } = useDeepAgent()
  const errorMessage = error ? (error instanceof Error ? error.message : String(error)) : null
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Find the last AI message that might still be streaming
  const lastAiMsg = [...messages].reverse().find(isAIMessage)
  const streamingId = isLoading ? lastAiMsg?.id : undefined

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-gray-900">DeepAgent</h1>
          <p className="text-xs text-gray-500">React frontend generator — describe it, I build it</p>
        </div>
        {isLoading && (
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
            Working...
          </span>
        )}
      </header>

      {/* Subagent status bar */}
      <SubagentStatus subagents={subagents} isLoading={isLoading} />

      {/* Error banner */}
      {errorMessage && (
        <div className="mx-4 mt-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
          Error: {errorMessage}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-lg">
              <Bot className="h-8 w-8" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">What should I build?</h2>
              <p className="mt-1 text-sm text-gray-500">
                Describe a web app and I'll generate a working React frontend.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 text-sm">
              {['A task tracker', 'A weather dashboard', 'A recipe app', 'A habit tracker'].map((example) => (
                <button
                  key={example}
                  onClick={() => sendMessage(`Build me ${example.toLowerCase()} with React`)}
                  className="rounded-full border border-gray-200 bg-white px-4 py-2 text-gray-600 transition-colors hover:bg-gray-50 hover:border-gray-300"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-4">
          {messages.map((msg, i) => (
            <ChatMessage
              key={msg.id ?? i}
              message={msg}
              isStreaming={msg.id === streamingId}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="mx-auto w-full max-w-3xl">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}