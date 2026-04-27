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
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
  id: string
}

export interface AIMessage extends BaseMessage {
  type?: string
  role?: string
  tool_calls?: ToolCall[]
}

export type Message = HumanMessage | ToolMessage | AIMessage

export const isHumanMessage = (m: Message): m is HumanMessage =>
  m.type === 'human' || (m as HumanMessage).role === 'user'

export const isToolMessage = (m: Message): m is ToolMessage =>
  m.type === 'tool' || m.type === 'ToolMessage'

export const isAIMessage = (m: Message): m is AIMessage =>
  !isHumanMessage(m) && !isToolMessage(m)

export function extractText(content: MessageContent): string {
  if (typeof content === 'string') return content
  return content
    .filter((b) => b.type === 'text' && b.text)
    .map((b) => b.text!)
    .join('\n')
}
