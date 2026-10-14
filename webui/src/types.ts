export interface Task {
  task_id: string
  projectID?: string | null
  keti?: 'keti2' | 'keti3' | null
  ip_name?: string
  ip_id?: string | null
  missing_directory?: boolean
  data_missing?: boolean
  prompt: string
  status: string
  created_at: string
  turn_id?: number
  chatstatus?: string
  verification_status?: string
  reports?: string[]
}
export interface Artifact { path: string; size: number; kind: 'report_html' | 'report_json' | 'file' }
export interface TaskDetail { task: Task; files: Artifact[] }
export interface ChatMessage {
  id: string
  kind: 'user' | 'assistant' | 'tool' | 'error'
  text: string
  turnId?: number
  userSource?: 'fallback' | 'explicit' | 'legacy'
  thinking?: string
  toolCallId?: string
  toolName?: string
  args?: string
  output?: string
  state?: 'running' | 'success' | 'error'
}
export interface ConversationState {
  items: ChatMessage[]
  nextId: number
  seenEvents: Set<number>
  assistants: Record<string, string | null>
  activeUser: string | null
  userCount: number
  legacyFirstSeen: boolean
}
export type TaskEvent = ({ type: 'agent'; data: Record<string, unknown> } | { type: 'error'; error: unknown } | { type: 'user'; message: unknown } | { type: 'status'; status: string }) & { turn_id?: number; event_id?: number }
export const isTerminal = (status: string) => ['idle', 'paused', 'completed', 'failed', 'error', 'cancelled', 'canceled', 'done', 'finished'].includes(status)
export function statusLabel(status: string) {
  return ({ idle: '对话结束', paused: '已暂停', created: '已创建', queued: '排队中', running: '运行中', completed: '已完成', failed: '失败', error: '错误', cancelled: '已取消', done: '已完成', finished: '已完成', missing: '数据缺失', pending: '待验证', passed: '验证通过', unverified: '未验证' } as Record<string, string>)[status] || status || '未知'
}

// 英文 IP 标识原样显示，旧任务退回任务 ID。
export const ipLabel = (task: Task) => task.ip_name || task.ip_id || task.task_id
