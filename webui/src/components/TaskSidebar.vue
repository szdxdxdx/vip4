<script setup lang="ts">
import type { Task } from '../types'
import { ipLabel, statusLabel } from '../types'
defineProps<{ tasks: Task[]; selectedId: string; loading: boolean; error: string; deletingId: string; deleteError: string }>()
defineEmits<{ select: [id: string]; refresh: [] }>()
</script>
<template>
  <aside class="panel sidebar" aria-label="任务列表">
    <div class="panel-heading">
      <h2>任务列表 <span class="count">{{ tasks.length }}</span></h2>
      <button class="icon-button" :disabled="loading" @click="$emit('refresh')" aria-label="刷新任务列表">{{ loading ? '加载中' : '刷新' }}</button>
    </div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <p v-if="deleteError" class="error-banner" role="alert">{{ deleteError }}</p>
    <div class="task-list" :aria-busy="loading">
      <div v-if="!tasks.length" class="empty small">{{ loading ? '正在读取任务…' : '暂无任务，请在项目验证中提交。' }}</div>
      <div v-for="item in tasks" :key="item.task_id" class="task-card"
        :class="{ selected: item.task_id === selectedId }">
        <button type="button" class="task-select"
          :aria-current="item.task_id === selectedId ? 'true' : undefined"
          :disabled="item.task_id === deletingId" @click="$emit('select', item.task_id)">
          <span class="task-identity">
            <strong :title="ipLabel(item)">{{ ipLabel(item) }}</strong>
            <span class="task-meta">
              <small :title="item.task_id">{{ item.task_id }}</small>
              <span class="status" :class="item.status">{{ item.missing_directory ? '实际目录已删除' : statusLabel(item.status) }}</span>
            </span>
          </span>
        </button>
      </div>
    </div>
  </aside>
</template>
