import type { ProjectProgress, ProjectResults, ProjectSource } from './projectTypes'

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
export function createProject(projectID: string, prompt: string, signal: AbortSignal, force = false, source: ProjectSource = 'keti2') {
  return request<{ projectID: string; status: 'accepted' }>('/project/create_project', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectID, ...(source === 'keti3' ? { source } : {}), ...(force ? { force: true } : {}), ...(prompt.trim() ? { prompt } : {}) }),
  })
}
export function deleteProject(projectID: string, signal: AbortSignal) {
  return request<{ projectID: string; status: 'deleted' }>('/project/delete_project', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectID }),
  })
}
export function getProjectProgress(id: string, signal: AbortSignal) {
  return request<ProjectProgress>(`/project/get_progress?projectID=${encodeURIComponent(id)}`, { signal })
}
export function getProjectResults(id: string, signal: AbortSignal) {
  return request<ProjectResults>(`/project/get_results?projectID=${encodeURIComponent(id)}`, { signal })
}
