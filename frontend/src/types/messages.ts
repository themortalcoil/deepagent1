export type ContentBlock = { type: string; text?: string }
export type MessageContent = string | ContentBlock[]

export interface BaseMessage {
  id?: string
  content: MessageContent
  name?: string
  additional_kwargs?: Record<string, unknown>
}

export interface HumanMessage extends BaseMessage {
  type: 'human'
  role?: 'user'
}

export interface ToolMessage extends BaseMessage {
  type: 'tool' | 'ToolMessage'
  role?: string
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
  id: string
}

// AIMessage uses `type?: string` (not a literal union) intentionally:
// LangChain emits AI messages with various `type` values across versions
// and message classes (e.g., 'ai', 'AIMessage', 'AIMessageChunk', and
// streaming variants). A literal union would silently reject valid messages.
// The trade-off: TypeScript cannot exhaustively narrow `Message` on `type`
// alone, and `isAIMessage` is therefore defined by exclusion. If a new
// message kind appears that should NOT render as AI, add it as a sibling
// interface and extend the predicates accordingly.
export interface AIMessage extends BaseMessage {
  type?: string
  role?: string
  tool_calls?: ToolCall[]
}

export type Message = HumanMessage | ToolMessage | AIMessage

export const isHumanMessage = (m: Message): m is HumanMessage =>
  m.type === 'human' || m.role === 'user'

export const isToolMessage = (m: Message): m is ToolMessage =>
  m.type === 'tool' || m.type === 'ToolMessage'

export const isAIMessage = (m: Message): m is AIMessage =>
  !isHumanMessage(m) && !isToolMessage(m)

export function extractText(content: MessageContent): string {
  if (typeof content === 'string') return content
  return content
    .filter((b): b is ContentBlock & { text: string } => b.type === 'text' && b.text != null)
    .map((b) => b.text)
    .join('\n')
}
