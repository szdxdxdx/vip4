import type { Task, TaskDetail, TaskEvent } from './types'

async function checked(response: Response): Promise<Response> {
  if (response.ok) return response
  let message = `请求失败（HTTP ${response.status}）`
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') message = data.detail
  } catch { /* Non-JSON server error. */ }
  throw new Error(message)
}
export async function listTasks(projectID = '', taskId = '', signal?: AbortSignal): Promise<Task[]> {
  const query = new URLSearchParams()
  if (projectID.trim()) query.set('projectID', projectID.trim())
  if (taskId.trim()) query.set('task_id', taskId.trim())
  return (await (await checked(await fetch(`/task/list_tasks${query.size ? `?${query}` : ''}`, { signal }))).json()).tasks
}
export async function listDataset(signal?: AbortSignal): Promise<{ ips: { ip_name: string }[]; tools: string[] }> {
  return (await checked(await fetch('/task/list_dataset', { signal }))).json()
}
export function taskZipUrl(id: string) {
  return `/task/download_task?task_id=${encodeURIComponent(id)}`
}
export async function getTask(id: string, signal?: AbortSignal): Promise<TaskDetail> {
  return (await checked(await fetch(`/task/get_task?task_id=${encodeURIComponent(id)}`, { signal }))).json()
}
export async function createTask(ipName: string, tool: string, userprompt: string, signal?: AbortSignal): Promise<{ task_id: string }> {
  return (await checked(await fetch('/task/create_task', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip_name: ipName, tool, userprompt }),
  }))).json()
}
export async function deleteTask(id: string): Promise<void> {
  await checked(await fetch(`/task/delete_task?task_id=${encodeURIComponent(id)}`, { method: 'DELETE' }))
}
export async function uploadToFactory(id: string): Promise<void> {
  const result = await (await checked(await fetch(`/task/upload_to_factory?task_id=${encodeURIComponent(id)}`, {
    method: 'POST',
  }))).json()
  if (result.success !== true) throw new Error('上传失败：服务端未确认成功')
}
export function fileUrl(id: string, path: string, download = false) {
  return `/task/get_file?task_id=${encodeURIComponent(id)}&path=${encodeURIComponent(path)}&download=${download}`
}
export async function streamTask(id: string, signal: AbortSignal, onEvent: (event: TaskEvent) => void): Promise<void> {
  const response = await checked(await fetch(`/task/get_events?task_id=${encodeURIComponent(id)}`, {
    signal, headers: { Accept: 'application/x-ndjson' },
  }))
  if (!response.body) throw new Error('服务端未返回事件流')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  function consume(line: string) {
    if (!line.trim() || signal.aborted) return
    try { onEvent(JSON.parse(line) as TaskEvent) }
    catch (error) { throw new Error(`事件流解析失败：${error instanceof Error ? error.message : String(error)}`) }
  }
  try {
    while (!signal.aborted) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let newline: number
      while ((newline = buffer.indexOf('\n')) >= 0) {
        consume(buffer.slice(0, newline))
        buffer = buffer.slice(newline + 1)
      }
      if (done) { consume(buffer); break }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export async function sendMessage(id: string, message: string): Promise<{ task_id: string; status: string }> {
  return (await checked(await fetch('/task/send_message', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: id, message }),
  }))).json()
}
export async function pauseTask(id: string): Promise<{ task_id: string; status: string }> {
  return (await checked(await fetch('/task/pause_task', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: id }),
  }))).json()
}
