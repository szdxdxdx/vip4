import type { ProjectSource } from './projectTypes'

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
export function createProject(projectID: string, userprompt: string, signal: AbortSignal, source: ProjectSource, tool: string) {
  return request<{ projectID: string; keti: ProjectSource; timestamp: string; status: 'accepted' }>('/project/create_project', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectID, source, userprompt, tool }),
  })
}
