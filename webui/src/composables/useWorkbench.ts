import { computed, onBeforeUnmount, ref } from 'vue'
import * as api from '../api'
import type { Artifact, Task } from '../types'
import { isTerminal } from '../types'
import { applyTaskEvent, initialConversation } from './eventReducer'

const errorText = (error: unknown) => error instanceof Error ? error.message : String(error)
export function useWorkbench() {
  const tasks = ref<Task[]>([])
  const selectedId = ref('')
  const task = ref<Task | null>(null)
  const files = ref<Artifact[]>([])
  const conversation = ref(initialConversation())
  const listLoading = ref(false)
  const detailLoading = ref(false)
  const streamState = ref<'idle' | 'connecting' | 'live' | 'closed' | 'error'>('idle')
  const listError = ref('')
  const detailError = ref('')
  const streamError = ref('')
  const createError = ref('')
  const creating = ref(false)
  const deletingId = ref('')
  const deleteError = ref('')
  const deletedIds = new Set<string>()
  let generation = 0
  let listGeneration = 0
  let controller: AbortController | undefined
  const messages = computed(() => conversation.value.items.filter(m => m.kind !== 'assistant' || m.text || m.thinking))

  async function refreshTasks() {
    const revision = ++listGeneration
    listLoading.value = true
    listError.value = ''
    try {
      const result = await api.listTasks()
      if (revision === listGeneration) {
        // 最新列表确认删除后释放标记，允许其他页面重建同 ID。
        for (const id of deletedIds) {
          if (!result.some(item => item.task_id === id)) deletedIds.delete(id)
        }
        const pending = tasks.value.find(item => item.task_id === deletingId.value)
        tasks.value = result.filter(item => !deletedIds.has(item.task_id))
        if (pending && !tasks.value.some(item => item.task_id === pending.task_id)) tasks.value.push(pending)
      }
    } catch (error) {
      if (revision === listGeneration) listError.value = errorText(error)
    } finally { if (revision === listGeneration) listLoading.value = false }
  }
  async function refreshDetail(id: string, version: number, signal: AbortSignal) {
    const result = await api.getTask(id, signal)
    if (version !== generation || signal.aborted) return false
    task.value = result.task
    files.value = result.files
    detailError.value = ''
    return true
  }
  // The event stream can end just before the backend commits final metadata.
  async function reconcile(id: string, version: number, signal: AbortSignal) {
    for (const delay of [0, 400, 1200, 2500]) {
      if (delay) await new Promise(resolve => setTimeout(resolve, delay))
      if (version !== generation || signal.aborted) return
      try {
        if (!await refreshDetail(id, version, signal)) return
      } catch (error) {
        if (version !== generation || signal.aborted) return
        detailError.value = errorText(error)
      }
      await refreshTasks()
      if (version !== generation || signal.aborted || (task.value && isTerminal(task.value.status))) return
    }
  }
  async function selectTask(id: string) {
    if (id === deletingId.value || deletedIds.has(id)) return
    controller?.abort() // Disconnect the subscription only; the backend task keeps running.
    const current = new AbortController()
    controller = current
    const version = ++generation
    selectedId.value = id
    task.value = null
    files.value = []
    conversation.value = initialConversation()
    detailError.value = streamError.value = ''
    detailLoading.value = true
    streamState.value = 'connecting'
    try {
      const result = await api.getTask(id, current.signal)
      if (version !== generation || current.signal.aborted) return
      task.value = result.task
      files.value = result.files
      conversation.value = initialConversation(result.task.prompt)
      detailLoading.value = false
    } catch (error) {
      if (version !== generation || current.signal.aborted) return
      detailError.value = errorText(error)
      detailLoading.value = false
      streamState.value = 'error'
      return
    }
    try {
      // Replay the full stream, even for completed tasks, without retaining raw events.
      await api.streamTask(id, current.signal, event => {
        if (version !== generation || current.signal.aborted) return
        streamState.value = 'live'
        applyTaskEvent(conversation.value, event)
      })
      if (version !== generation || current.signal.aborted) return
      streamState.value = 'closed'
    } catch (error) {
      if (version !== generation || current.signal.aborted) return
      streamState.value = 'error'
      streamError.value = errorText(error)
    }
    await reconcile(id, version, current.signal)
  }
  async function removeTask(id: string) {
    if (deletingId.value || deletedIds.has(id)) return
    if (!window.confirm(`永久删除任务「${id}」？全部文件不可恢复，运行任务将先停止。`)) return
    deletingId.value = id
    deleteError.value = ''
    const interrupted = selectedId.value === id
    if (interrupted) {
      controller?.abort()
      generation++
      detailLoading.value = false
      streamState.value = 'idle'
    }
    try {
      await api.deleteTask(id)
    } catch (error) {
      deleteError.value = `永久删除任务「${id}」失败：${errorText(error)}`
      deletingId.value = ''
      if (interrupted && selectedId.value === id) void selectTask(id)
      return
    }
    deletedIds.add(id)
    // 作废删除前的列表请求，避免旧快照复活已删除任务。
    listGeneration++
    tasks.value = tasks.value.filter(item => item.task_id !== id)
    deletingId.value = ''
    if (selectedId.value === id) {
      controller?.abort()
      generation++
      selectedId.value = ''
      task.value = null
      files.value = []
      conversation.value = initialConversation()
      detailLoading.value = false
      streamState.value = 'idle'
      detailError.value = streamError.value = ''
      if (tasks.value[0]) void selectTask(tasks.value[0].task_id)
    }
    await refreshTasks()
  }
  async function submit(id: string, prompt: string) {
    if (creating.value) return false
    creating.value = true
    createError.value = ''
    try {
      await api.createTask(id.trim(), prompt.replaceAll('<task_id>', id.trim()))
      deletedIds.delete(id.trim())
      await refreshTasks()
      void selectTask(id.trim())
      return true
    } catch (error) { createError.value = errorText(error); return false }
    finally { creating.value = false }
  }
  async function initialize() {
    await refreshTasks()
    if (!selectedId.value && tasks.value[0]) void selectTask(tasks.value[0].task_id)
  }
  async function refreshSelected() {
    if (!selectedId.value || !controller) return
    const version = generation
    try { await refreshDetail(selectedId.value, version, controller.signal) }
    catch (error) { if (version === generation && !controller.signal.aborted) detailError.value = errorText(error) }
  }
  onBeforeUnmount(() => { generation++; listGeneration++; controller?.abort() })
  return { tasks, selectedId, task, files, messages, listLoading, detailLoading, streamState,
    listError, detailError, streamError, createError, creating, deletingId, deleteError, removeTask, refreshTasks, selectTask,
    submit, initialize, refreshSelected }
}
