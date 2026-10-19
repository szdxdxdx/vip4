import type { Keti5 } from './keti5'
import type { ProjectBatch, ProjectSource } from './projectTypes'

async function request<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    let message = `请求失败（HTTP ${response.status}）`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') message = data.detail
    } catch { /* 非 JSON 错误保留 HTTP 状态。 */ }
    throw new Error(message)
  }
  return response.json()
}
export function createProject(projectID: string, userprompt: string, signal: AbortSignal, source: ProjectSource, tool: string, keti5: Keti5 | null = null) {
  return request<{ projectID: string; keti: ProjectSource; timestamp: string; status: 'accepted' }>('/project/create_project', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectID, source, userprompt, tool, ...(keti5 ? { keti5 } : {}) }),
  })
}

export function getProgress(projectID: string, source: ProjectSource, signal: AbortSignal) {
  const query = new URLSearchParams({ projectID, source })
  return request<{ batches: ProjectBatch[] }>(`/project/get_progress?${query}`, { signal })
}
