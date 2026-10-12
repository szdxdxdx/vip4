<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import TaskSidebar from './components/TaskSidebar.vue'
import ConversationPanel from './components/ConversationPanel.vue'
import TaskComposer from './components/TaskComposer.vue'
import ArtifactPanel from './components/ArtifactPanel.vue'
import ProgressPanel from './components/ProgressPanel.vue'
import { useWorkbench } from './composables/useWorkbench'
const { tasks, selectedId, task, files, messages, listLoading, detailLoading, streamState,
  listError, detailError, streamError, createError, creating, deletingId, deleteError, removeTask, refreshTasks, selectTask,
  submit, initialize, refreshSelected } = useWorkbench()
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
    <header class="app-header"><h1>软件IP验证</h1></header>
    <main class="workspace">
      <TaskSidebar
        :tasks="tasks" :selected-id="selectedId" :loading="listLoading" :error="listError"
        :deleting-id="deletingId" :delete-error="deleteError"
        @select="selectTask" @refresh="refreshTasks" @delete="removeTask"
      />
      <div id="main-view" class="panel center-panel">
        <ConversationPanel
          v-show="activeView === 'conversation'" :active="activeView === 'conversation'"
          :task="task" :selected-id="selectedId" :messages="messages"
          :loading="detailLoading" :error="detailError" :stream-error="streamError"
          :stream-state="streamState" @replay="selectTask(selectedId)"
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
      <aside class="panel task-controls" aria-label="任务输入与视图切换">
        <TaskComposer :creating="creating" :error="createError" @submit="submit" />
        <nav class="view-controls" aria-label="主区域视图">
          <button
            v-for="view in views" :key="view.id" type="button"
            :class="{ active: activeView === view.id }" :aria-pressed="activeView === view.id"
            aria-controls="main-view" @click="activeView = view.id"
          >{{ view.label }}</button>
        </nav>
      </aside>
    </main>
  </div>
</template>
