import type { ChatMessage, ConversationState, TaskEvent } from '../types'

const OUTPUT_LIMIT = 24000
function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}
function stringify(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}
export function truncate(value: string): string {
  return value.length > OUTPUT_LIMIT ? value.slice(0, OUTPUT_LIMIT) + '\n…（输出已截断，请下载文件查看完整内容）' : value
}
function output(value: unknown): string {
  const content = record(value).content
  if (Array.isArray(content)) return truncate(content.map(block => {
    const b = record(block)
    return b.type === 'text' ? stringify(b.text) : b.type === 'image' ? '[图片输出]' : stringify(b)
  }).join('\n'))
  return truncate(stringify(value))
}
export function initialConversation(prompt = ''): ConversationState {
  return { items: prompt ? [{ id: 'prompt', kind: 'user', text: prompt }] : [], activeAssistant: null, nextId: 0 }
}
function add(state: ConversationState, message: Omit<ChatMessage, 'id'>): ChatMessage {
  const item = { ...message, id: `event-${state.nextId++}` }
  state.items.push(item)
  return item
}
function assistant(state: ConversationState): ChatMessage {
  let item = state.items.find(m => m.id === state.activeAssistant)
  if (!item) { item = add(state, { kind: 'assistant', text: '', thinking: '' }); state.activeAssistant = item.id }
  return item
}
function snapshot(item: ChatMessage, message: Record<string, unknown>) {
  if (!Array.isArray(message.content)) return
  item.text = message.content.filter(b => record(b).type === 'text').map(b => stringify(record(b).text)).join('')
  item.thinking = message.content.filter(b => record(b).type === 'thinking').map(b => stringify(record(b).thinking)).join('')
}
export function applyTaskEvent(state: ConversationState, wrapper: TaskEvent): void {
  if (wrapper.type === 'error') { add(state, { kind: 'error', text: output(wrapper.error) || '任务发生错误' }); return }
  if (wrapper.type !== 'agent') return
  const event = record(wrapper.data)
  const message = record(event.message)
  if (event.type === 'message_start' && message.role === 'assistant') {
    state.activeAssistant = null
    snapshot(assistant(state), message)
  } else if (event.type === 'message_update') {
    if (message.role && message.role !== 'assistant') return
    const delta = record(event.assistantMessageEvent)
    if (delta.type === 'text_delta') assistant(state).text += stringify(delta.delta)
    if (delta.type === 'thinking_delta') {
      const item = assistant(state)
      item.thinking = (item.thinking || '') + stringify(delta.delta)
    }
  } else if (event.type === 'message_end' && message.role === 'assistant') {
    snapshot(assistant(state), message)
    if (message.errorMessage) add(state, { kind: 'error', text: output(message.errorMessage) })
    state.activeAssistant = null
  } else if (['tool_execution_start', 'tool_execution_update', 'tool_execution_end'].includes(String(event.type))) {
    const id = stringify(event.toolCallId)
    if (!id) return
    let tool = state.items.find(m => m.kind === 'tool' && m.toolCallId === id)
    if (!tool) tool = add(state, { kind: 'tool', text: '', toolCallId: id, toolName: stringify(event.toolName) || '工具', state: 'running' })
    if (event.toolName) tool.toolName = stringify(event.toolName)
    if (event.args !== undefined) tool.args = truncate(stringify(event.args))
    if (event.type === 'tool_execution_update') tool.output = output(event.partialResult)
    if (event.type === 'tool_execution_end') {
      tool.output = output(event.result)
      tool.state = event.isError ? 'error' : 'success'
    }
  } else if (event.type === 'error') {
    add(state, { kind: 'error', text: output(event.error ?? event.message) || 'Agent 发生错误' })
  }
  // User prompts come exclusively from task metadata. RPC control events are not messages.
}
