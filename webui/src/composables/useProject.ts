import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { createTask, listDataset, listTasks } from '../api'
import { createProject, getProgress } from '../projectApi'
import type { ProjectBatch, ProjectSource } from '../projectTypes'
import { batchStatusLabel, type Task } from '../types'

export function useProject(active: Ref<boolean>, onChanged: () => void = () => {}) {
  const source = ref<'local' | ProjectSource>('local')
  const projectID = ref(''), ip = ref(''), tool = ref('CBMC'), prompt = ref('')
  const dataset = ref<string[]>([]), tasks = ref<Task[]>([])
  const queryID = ref(''), queryTaskID = ref('')
  const error = ref(''), listError = ref(''), busy = ref(false), loading = ref(false)
  const batches = ref<ProjectBatch[]>([])
  const messages = ref<Readonly<{ id: number; text: string; error: boolean }>[]>([])
  let messageID = 0
  const snapshots = new Map<string, string>()
  function appendMessage(text: string, error = false) {
    messages.value = [...messages.value, Object.freeze({ id: ++messageID, text, error })]
  }
  function logBatch(batch: ProjectBatch, requestFailed = false) {
    const key = JSON.stringify([batch.keti, batch.projectID, batch.timestamp])
    const ids = batch.tasks?.map(task => task.task_id) || []
    const snapshot = JSON.stringify([batch.status, batch.error || '', ids])
    if (!requestFailed && snapshots.get(key) === snapshot) return
    snapshots.set(key, snapshot)
    appendMessage(`${ids.length ? ids.join('、') + '：' : ''}${batchStatusLabel(batch.status)}${batch.error ? '；' + batch.error : ''}`, !!batch.error)
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  let disposed = false, revision = 0
  function cancelTimer() { clearTimeout(timer); timer = undefined }
  let controller: AbortController | undefined
  const mutationController = new AbortController()
  const message = (cause: unknown) => cause instanceof Error ? cause.message : String(cause)
  function cancelList() {
    revision++
    controller?.abort()
    loading.value = false
  }
  async function refresh() {
    cancelList()
    if (!active.value || disposed) return
    const version = revision, abort = new AbortController()
    controller = abort
    loading.value = true
    listError.value = ''
    try {
      const submitted = batches.value.slice()
      // 同来源同项目只查询一次，再按时间戳精确匹配，避免混入历史批次。
      const groups = [...new Map(submitted.map(batch => [JSON.stringify([batch.keti, batch.projectID]), batch])).values()]
      const [result, progress] = await Promise.all([
        listTasks(queryID.value, queryTaskID.value, abort.signal),
        Promise.all(groups.map(async batch => {
          try { return { batch, result: await getProgress(batch.projectID, batch.keti, abort.signal) } }
          catch (cause) { return { batch, error: `批次状态读取失败：${message(cause)}` } }
        })),
      ])
      if (version === revision && !disposed) {
        tasks.value = result
        batches.value = batches.value.map(batch => {
          const group = progress.find(item => item.batch.keti === batch.keti && item.batch.projectID === batch.projectID)
          if (!group || !submitted.some(item => item.keti === batch.keti && item.projectID === batch.projectID && item.timestamp === batch.timestamp)) return batch
          const match = group.result?.batches.find(item => item.timestamp === batch.timestamp)
          const updated = match ? { ...batch, ...match, error: match.error } :
            { ...batch, error: group.error || '未找到本次提交批次，请稍后手动刷新' }
          logBatch(updated, !!group.error)
          return updated
        })
      }
    } catch (cause) {
      if (version === revision && !disposed) { listError.value = message(cause); appendMessage(listError.value, true) }
    } finally {
      if (version === revision && !disposed) {
        loading.value = false
      }
    }
  }
  async function submit() {
    if (busy.value || !active.value) return
    const selectedSource = source.value, id = projectID.value.trim(), submittedRevision = revision
    error.value = ''
    if (selectedSource === 'local' ? !ip.value : !id) {
      error.value = selectedSource === 'local' ? '请选择数据集 IP' : '请输入项目 ID'
      appendMessage(error.value, true)
      return
    }
    busy.value = true
    appendMessage('请求中…')
    try {
      if (selectedSource === 'local') {
        const task = await createTask(ip.value, tool.value, prompt.value, mutationController.signal)
        if (disposed) return
        appendMessage(`${task.task_id}：提交成功`)
      }
      else {
        const batch = await createProject(id, prompt.value, mutationController.signal, selectedSource, tool.value)
        if (disposed) return
        batches.value.push(batch)
        logBatch(batch)
        if (active.value && revision === submittedRevision) {
          cancelTimer()
          timer = setTimeout(() => {
            timer = undefined
            if (!disposed && active.value && revision === submittedRevision) void refresh()
          }, 1000)
        }
      }
      if (disposed) return
      onChanged()
    } catch (cause) {
      if (!disposed) { error.value = message(cause); appendMessage(error.value, true) }
    } finally { if (!disposed) busy.value = false }
  }
  const datasetController = new AbortController()
  void listDataset(datasetController.signal).then(result => {
    if (!disposed) dataset.value = result.ips.map(item => item.ip_name)
  }).catch(cause => { if (!disposed) { error.value = `数据集读取失败：${message(cause)}`; appendMessage(error.value, true) } })
  watch([queryID, queryTaskID], () => { cancelTimer(); cancelList(); tasks.value = []; listError.value = '' }, { flush: 'sync' })
  watch(active, enabled => { if (!enabled) { cancelTimer(); cancelList() } }, { flush: 'sync' })
  onBeforeUnmount(() => { disposed = true; cancelTimer(); cancelList(); datasetController.abort(); mutationController.abort() })
  return { messages, batches, source, projectID, ip, tool, prompt, dataset, tasks, queryID, queryTaskID, error, busy,
    listError, loading, refresh, submit }
}
