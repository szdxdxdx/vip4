import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { createProject, getProjectProgress, getProjectResults } from '../projectApi'
import { isProjectTerminal, type ProjectProgress, type ProjectResults } from '../projectTypes'

export function useProject(active: Ref<boolean>, onForced: () => void = () => {}) {
  const projectID = ref('')
  const prompt = ref('')
  const progress = ref<ProjectProgress | null>(null)
  const results = ref<ProjectResults | null>(null)
  const error = ref('')
  const busy = ref(false)
  const polling = ref(false)
  let generation = 0
  let disposed = false
  let controller: AbortController | undefined
  let timer: ReturnType<typeof setTimeout> | undefined
  let pending: 'create' | 'force' | 'query' | undefined

  function cancel() {
    generation++
    controller?.abort()
    clearTimeout(timer)
    timer = undefined
    pending = undefined
  }
  // 即使传输层忽略 abort，也要等旧请求结束后再发下一次请求。
  async function drain() {
    if (disposed || !active.value || busy.value || !pending) return
    const action = pending
    pending = undefined
    const id = projectID.value.trim()
    const token = generation
    const abort = new AbortController()
    controller = abort
    busy.value = true
    const current = () => !disposed && active.value && token === generation
    try {
      if (action === 'create' || action === 'force') {
        await createProject(id, prompt.value, abort.signal, action === 'force')
        // 创建已生效，即使此时隐藏或换 ID，也须清理工作台旧快照。
        if (action === 'force' && !disposed) onForced()
        if (!current()) return
      }
      const nextProgress = await getProjectProgress(id, abort.signal)
      if (!current()) return
      progress.value = nextProgress
      const nextResults = await getProjectResults(id, abort.signal)
      if (!current()) return
      results.value = nextResults
      polling.value = !isProjectTerminal(nextProgress.status)
      if (polling.value) timer = setTimeout(() => {
        timer = undefined
        pending = 'query'
        void drain()
      }, 2000)
    } catch (cause) {
      if (current()) {
        error.value = cause instanceof Error ? cause.message : String(cause)
        polling.value = false
      }
    } finally {
      busy.value = false
      if (controller === abort) controller = undefined
      void drain()
    }
  }
  function start(action: 'create' | 'force' | 'query') {
    if ((action === 'create' || action === 'force') && busy.value) return
    cancel()
    error.value = ''
    if (!projectID.value.trim()) {
      error.value = '请输入项目 ID'
      polling.value = false
      return
    }
    polling.value = true
    if (action !== 'query') { progress.value = null; results.value = null }
    pending = action
    void drain()
  }
  watch(projectID, () => {
    cancel()
    polling.value = false
    progress.value = null
    results.value = null
    error.value = ''
  }, { flush: 'sync' })
  watch(active, enabled => {
    cancel()
    if (enabled && polling.value) { pending = 'query'; void drain() }
  }, { flush: 'sync' })
  onBeforeUnmount(() => { disposed = true; cancel() })
  function forceSubmit() {
    if (!active.value || busy.value || !projectID.value.trim()) return
    if (!window.confirm(`强制提交项目「${projectID.value.trim()}」？将先停止旧验证，永久删除该项目全部旧任务文件及数据库映射，不可恢复。`)) return
    start('force')
  }
  return { projectID, prompt, progress, results, error, busy, polling,
    submit: () => start('create'), forceSubmit, query: () => start('query') }
}
