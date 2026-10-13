export type ProjectStatus = 'accepted' | 'collecting' | 'running' | 'completed' | 'failed' | 'cancelled' | 'empty'
export type ProjectTaskStatus = 'created' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'deleted'
export interface ProjectTask {
  task_id: string
  status: ProjectTaskStatus
  created_at?: string
  prompt?: string
  reports?: unknown
}
export interface ProjectProgress {
  projectID: string
  status: ProjectStatus
  error?: string
  total: number
  finished: number
  tasks: ProjectTask[]
}
export interface ProjectFile { path: string; size: number; kind: string; download_url: string }
export interface ProjectResults {
  projectID: string
  tasks: { task_id: string; status: ProjectTaskStatus; files: ProjectFile[] }[]
}
export const projectLabels: Record<ProjectStatus | ProjectTaskStatus, string> = {
  accepted: '已受理', collecting: '收集中', running: '验证中', completed: '已完成',
  failed: '失败', cancelled: '已取消', empty: '无任务', created: '已创建', queued: '排队中', deleted: '已删除',
}
export const isProjectTerminal = (status: ProjectStatus) =>
  ['completed', 'failed', 'cancelled', 'empty'].includes(status)
