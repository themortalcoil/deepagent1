import { useState } from 'react'
import { SendHorizontal } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled = false, placeholder = 'Describe the app you want to build...' }: ChatInputProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-gray-200 bg-white px-4 py-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <SendHorizontal className="h-4 w-4" />
      </button>
    </form>
  )
}