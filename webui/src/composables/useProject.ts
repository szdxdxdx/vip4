import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { createTask, listDataset, listTasks } from '../api'
import { createProject, deleteProject } from '../projectApi'
import type { ProjectSource } from '../projectTypes'
import type { Task } from '../types'

export function useProject(active: Ref<boolean>, onChanged: () => void = () => {}) {
  const source = ref<'local' | ProjectSource>('local')
  const projectID = ref(''), ip = ref(''), tool = ref('CBMC'), prompt = ref('')
  const dataset = ref<string[]>([]), tasks = ref<Task[]>([])
  const queryID = ref(''), queryTaskID = ref('')
  const error = ref(''), listError = ref(''), busy = ref(false), loading = ref(false)
  let disposed = false, revision = 0
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
      const result = await listTasks(queryID.value, queryTaskID.value, abort.signal)
      if (version === revision && !disposed) tasks.value = result
    } catch (cause) {
      if (version === revision && !disposed) listError.value = message(cause)
    } finally {
      if (version === revision && !disposed) {
        loading.value = false
      }
    }
  }
  async function act(action: 'create' | 'force' | 'delete') {
    if (busy.value || !active.value) return
    const selectedSource = source.value, id = projectID.value.trim()
    error.value = ''
    if (selectedSource === 'local' ? !ip.value : !id) {
      error.value = selectedSource === 'local' ? '请选择数据集 IP' : '请输入项目 ID'
      return
    }
    if (action !== 'create') {
      if (selectedSource === 'local') return
      const verb = action === 'force' ? '强制提交' : '删除'
      if (!window.confirm(`${verb}「${selectedSource} / ${id}」？将停止验证并永久删除该来源、该项目的全部任务文件；其他来源不受影响，不可恢复。`)) return
    }
    busy.value = true
    try {
      if (selectedSource === 'local') await createTask(ip.value, tool.value, prompt.value, mutationController.signal)
      else if (action === 'delete') await deleteProject(id, selectedSource, mutationController.signal)
      else await createProject(id, prompt.value, mutationController.signal, action === 'force', selectedSource, tool.value)
      if (disposed) return
      onChanged()
    } catch (cause) {
      if (!disposed) error.value = message(cause)
    } finally { if (!disposed) busy.value = false }
  }
  const datasetController = new AbortController()
  void listDataset(datasetController.signal).then(result => {
    if (!disposed) dataset.value = result.ips.map(item => item.ip_name)
  }).catch(cause => { if (!disposed) error.value = `数据集读取失败：${message(cause)}` })
  watch([queryID, queryTaskID], () => { cancelList(); tasks.value = []; listError.value = '' }, { flush: 'sync' })
  watch(active, enabled => { if (!enabled) cancelList() }, { flush: 'sync' })
  onBeforeUnmount(() => { disposed = true; cancelList(); datasetController.abort(); mutationController.abort() })
  return { source, projectID, ip, tool, prompt, dataset, tasks, queryID, queryTaskID, error, busy,
    listError, loading, refresh, submit: () => act('create'), forceSubmit: () => act('force'), removeProject: () => act('delete') }
}
