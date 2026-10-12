<script setup lang="ts">
import { onMounted } from 'vue'
import TaskSidebar from './components/TaskSidebar.vue'
import ConversationPanel from './components/ConversationPanel.vue'
import TaskComposer from './components/TaskComposer.vue'
import ArtifactPanel from './components/ArtifactPanel.vue'
import { useWorkbench } from './composables/useWorkbench'
const { tasks, selectedId, task, files, messages, listLoading, detailLoading, streamState,
  listError, detailError, streamError, createError, creating, refreshTasks, selectTask,
  submit, initialize, refreshSelected } = useWorkbench()
onMounted(initialize)
</script>
<template>
  <div class="workbench">
    <header class="app-header"><div class="brand"><span class="brand-mark">V</span><div><h1>Agent 验证工作台</h1><p>软件 IP 验证 · 任务 / 会话 / 产物</p></div></div><span class="header-tag">VIP4 <span>WORKSPACE</span></span></header>
    <main class="workspace">
      <TaskSidebar :tasks="tasks" :selected-id="selectedId" :loading="listLoading" :error="listError" @select="selectTask" @refresh="refreshTasks" />
      <div class="panel center-panel"><ConversationPanel :task="task" :selected-id="selectedId" :messages="messages" :loading="detailLoading" :error="detailError" :stream-error="streamError" :stream-state="streamState" @replay="selectTask(selectedId)" /><TaskComposer :creating="creating" :error="createError" @submit="submit" /></div>
      <ArtifactPanel :task-id="selectedId" :files="files" :loading="detailLoading" :error="detailError" @refresh="refreshSelected" />
    </main>
  </div>
</template>
