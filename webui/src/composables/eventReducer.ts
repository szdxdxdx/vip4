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
export function initialConversation(): ConversationState {
  return { items: [], nextId: 0, seenEvents: new Set(), assistants: {}, activeUser: null }
}
function add(state: ConversationState, message: Omit<ChatMessage, 'id'>): ChatMessage {
  const item = { ...message, id: `event-${state.nextId++}` }
  state.items.push(item)
  return item
}
function assistant(state: ConversationState, turnId?: number): ChatMessage {
  const key = String(turnId ?? 'legacy')
  let item = state.items.find(m => m.id === state.assistants[key])
  if (!item) {
    item = add(state, { kind: 'assistant', text: '', thinking: '', turnId })
    state.assistants[key] = item.id
  }
  return item
}
function snapshot(item: ChatMessage, message: Record<string, unknown>) {
  if (!Array.isArray(message.content)) return
  item.text = message.content.filter(b => record(b).type === 'text').map(b => stringify(record(b).text)).join('')
  item.thinking = message.content.filter(b => record(b).type === 'thinking').map(b => stringify(record(b).thinking)).join('')
}
function userText(content: unknown): string {
  return Array.isArray(content) ? content.filter(b => record(b).type === 'text').map(b => stringify(record(b).text)).join('') : stringify(content)
}
function user(state: ConversationState, text: string, turnId: number | undefined, source: 'explicit' | 'legacy', ending = false) {
  // start/end 合并一条 RPC 消息；显式输入只与尚未确认的同文 RPC 配对。
  const active = state.items.find(m => m.id === state.activeUser)
  if (source === 'legacy' && ending && active) {
    if (active.userSource === 'legacy') active.text = text
    state.activeUser = null
    return
  }
  const duplicate = state.items.find((m, index) => m.kind === 'user' && m.text === text &&
    (m.turnId === turnId || m.turnId === undefined || turnId === undefined) &&
    m.userSource !== source && !m.userConfirmed &&
    (source !== 'explicit' || !state.items.slice(index + 1).some(item => item.kind !== 'user')))
  let item: ChatMessage
  if (duplicate) {
    item = duplicate
    item.userConfirmed = true
    if (source === 'explicit') { item.userSource = source; item.turnId = turnId }
  } else item = add(state, { kind: 'user', text, turnId, userSource: source })
  state.activeUser = source === 'legacy' && !ending ? item.id : null
}
export function applyTaskEvent(state: ConversationState, wrapper: TaskEvent): void {
  if (wrapper.event_id !== undefined) {
    if (state.seenEvents.has(wrapper.event_id)) return
    state.seenEvents.add(wrapper.event_id)
  }
  const turn = wrapper.turn_id
  if (wrapper.type === 'user') { user(state, userText(wrapper.message), turn, 'explicit'); return }
  if (wrapper.type === 'error') { add(state, { kind: 'error', text: output(wrapper.error) || '任务发生错误' }); return }
  if (wrapper.type !== 'agent') return
  const event = record(wrapper.data)
  const message = record(event.message)
  if (['message_start', 'message_end'].includes(String(event.type)) && message.role === 'user') {
    user(state, userText(message.content), turn, 'legacy', event.type === 'message_end')
    return
  }
  if (event.type === 'message_start' && message.role === 'assistant') {
    state.assistants[String(turn ?? 'legacy')] = null
    snapshot(assistant(state, turn), message)
  } else if (event.type === 'message_update') {
    if (message.role && message.role !== 'assistant') return
    const delta = record(event.assistantMessageEvent)
    if (delta.type === 'text_delta') assistant(state, turn).text += stringify(delta.delta)
    if (delta.type === 'thinking_delta') {
      const item = assistant(state, turn)
      item.thinking = (item.thinking || '') + stringify(delta.delta)
    }
  } else if (event.type === 'message_end' && message.role === 'assistant') {
    snapshot(assistant(state, turn), message)
    if (message.errorMessage) add(state, { kind: 'error', text: output(message.errorMessage) })
    state.assistants[String(turn ?? 'legacy')] = null
  } else if (['tool_execution_start', 'tool_execution_update', 'tool_execution_end'].includes(String(event.type))) {
    const id = stringify(event.toolCallId)
    if (!id) return
    let tool = state.items.find(m => m.kind === 'tool' && m.toolCallId === id && m.turnId === turn)
    if (!tool) tool = add(state, { kind: 'tool', text: '', toolCallId: id, turnId: turn, toolName: stringify(event.toolName) || '工具', state: 'running' })
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
  // RPC 控制事件不作为消息。
}
