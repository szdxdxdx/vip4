export interface Keti5 {
  projectId: string
  jobName: string
  buildId: string
  toolName: string
  executionId: string
}
const keys = ['projectId', 'jobName', 'buildId', 'toolName', 'executionId'] as const

// 五项必须同时非空；校验不改变传递的原字符串。
export function readKeti5(search: string): Keti5 | null {
  const query = new URLSearchParams(search)
  const values = keys.map(key => query.get(key))
  if (!values.every(value => typeof value === 'string' && value.trim().length > 0)) return null
  return Object.fromEntries(keys.map((key, index) => [key, values[index]])) as unknown as Keti5
}
