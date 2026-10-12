export interface Task {
  task_id: string
  prompt: string
  status: string
  created_at: string
  reports?: string[]
}
export interface Artifact { path: string; size: number; kind: 'report_html' | 'report_json' | 'file' }
export interface TaskDetail { task: Task; files: Artifact[] }
export interface ChatMessage {
  id: string
  kind: 'user' | 'assistant' | 'tool' | 'error'
  text: string
  thinking?: string
  toolCallId?: string
  toolName?: string
  args?: string
  output?: string
  state?: 'running' | 'success' | 'error'
}
export interface ConversationState {
  items: ChatMessage[]
  activeAssistant: string | null
  nextId: number
}
export type TaskEvent = { type: 'agent'; data: Record<string, unknown> } | { type: 'error'; error: unknown }
export const isTerminal = (status: string) => ['completed', 'failed', 'error', 'cancelled', 'canceled', 'done', 'finished'].includes(status)
export function statusLabel(status: string) {
  return ({ created: '已创建', queued: '排队中', running: '运行中', completed: '已完成', failed: '失败', error: '错误', cancelled: '已取消', done: '已完成', finished: '已完成' } as Record<string, string>)[status] || status || '未知'
}
