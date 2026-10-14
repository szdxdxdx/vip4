export type ProjectSource = 'keti2' | 'keti3'

// 批次独立于任务，查询或打包期间可能尚无 taskID。
export interface ProjectBatch {
  projectID: string
  keti: ProjectSource
  timestamp: string
  status: string
  error?: string
  total?: number
  tasks?: { task_id: string }[]
}
