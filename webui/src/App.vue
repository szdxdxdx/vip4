<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TaskSidebar from './components/TaskSidebar.vue'
import ConversationPanel from './components/ConversationPanel.vue'
import ArtifactPanel from './components/ArtifactPanel.vue'
import ProgressPanel from './components/ProgressPanel.vue'
import ProjectPanel from './components/ProjectPanel.vue'
import { useWorkbench } from './composables/useWorkbench'
const { tasks, selectedId, task, files, messages, listLoading, detailLoading, streamState,
  listError, detailError, streamError, deletingId, deleteError, removeTask, refreshTasks, selectTask,
  draft, chatBusy, chatError, canSend, canPause, sendMessage, pauseTask,
  initialize, resetHistory, refreshSelected } = useWorkbench()
// 详情接口可能缺少归属，使用当前选中任务的列表记录补齐。
const displayTask = computed(() => {
  const listed = tasks.value.find(item => item.task_id === selectedId.value)
  if (!task.value) return listed || null
  return { ...task.value, ip_name: task.value.ip_name || listed?.ip_name,
    ip_id: task.value.ip_id || listed?.ip_id,
    projectID: task.value.projectID ?? listed?.projectID, keti: task.value.keti ?? listed?.keti }
})
function viewTask(id: string) {
  activeView.value = 'conversation'
  void selectTask(id)
}
const mode = ref<'single' | 'project'>('project')
function viewProjectTask(id: string) {
  mode.value = 'single'
  activeView.value = 'conversation'
  void selectTask(id)
  void refreshTasks()
}
const activeView = ref<'conversation' | 'progress' | 'report' | 'files'>('conversation')
const views = [
  { id: 'conversation', label: '对话' },
  { id: 'progress', label: '进度预览' },
  { id: 'report', label: '验证结果报告' },
  { id: 'files', label: '文件下载' },
] as const
watch(selectedId, () => { activeView.value = 'conversation' }, { flush: 'sync' })
onMounted(initialize)
</script>
<template>
  <div class="workbench">
    <header class="app-header">
      <h1>软件IP验证</h1>
      <nav class="mode-controls" aria-label="验证模式">
        <button type="button" :class="{ active: mode === 'single' }" :aria-pressed="mode === 'single'" @click="mode = 'single'">任务详情</button>
        <button type="button" :class="{ active: mode === 'project' }" :aria-pressed="mode === 'project'" @click="mode = 'project'">项目验证</button>
      </nav>
    </header>
    <main v-show="mode === 'single'" class="workspace">
      <TaskSidebar
        :tasks="tasks" :selected-id="selectedId" :loading="listLoading" :error="listError"
        :deleting-id="deletingId" :delete-error="deleteError"
        @select="viewTask" @refresh="refreshTasks"
      />
      <div id="main-view" class="panel center-panel">
        <ConversationPanel
          v-show="activeView === 'conversation'" :active="mode === 'single' && activeView === 'conversation'"
          :task="displayTask" :selected-id="selectedId" :messages="messages"
          :loading="detailLoading" :error="detailError" :stream-error="streamError"
          :stream-state="streamState" v-model:draft="draft" :chat-busy="chatBusy" :chat-error="chatError"
          :can-send="canSend" :can-pause="canPause" :deleting="deletingId === selectedId && !!selectedId"
          @send="sendMessage" @pause="pauseTask" @replay="selectTask(selectedId)"
        />
        <ProgressPanel
          v-if="activeView === 'progress'" :task="task" :selected-id="selectedId"
          :messages="messages" :stream-state="streamState" :loading="detailLoading"
          :error="detailError || streamError"
        />
        <ArtifactPanel
          v-if="activeView === 'report' || activeView === 'files'" :view="activeView"
          :task-id="selectedId" :files="files" :loading="detailLoading" :error="detailError"
          @refresh="refreshSelected"
        />
      </div>
      <aside class="panel task-controls" aria-label="详情视图切换">
        <nav class="view-controls" aria-label="主区域视图">
          <button
            v-for="view in views" :key="view.id" type="button"
            :class="{ active: activeView === view.id }" :aria-pressed="activeView === view.id"
            aria-controls="main-view" @click="activeView = view.id"
          >{{ view.label }}</button>
        </nav>
        <section class="task-danger" aria-label="任务删除">
          <button type="button" :disabled="!selectedId || !!deletingId"
            :aria-label="selectedId ? `永久删除任务 ${selectedId}` : '删除当前任务'"
            :aria-busy="!!deletingId" @click="removeTask(selectedId)">
            {{ deletingId ? '删除中…' : '删除当前任务' }}
          </button>
        </section>
      </aside>
    </main>
    <ProjectPanel v-show="mode === 'project'" :active="mode === 'project'" @view-task="viewProjectTask" @changed="resetHistory" />
  </div>
</template>
