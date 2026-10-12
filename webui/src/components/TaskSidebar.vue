<script setup lang="ts">
import type { Task } from '../types'
import { statusLabel } from '../types'
defineProps<{ tasks: Task[]; selectedId: string; loading: boolean; error: string; deletingId: string; deleteError: string }>()
defineEmits<{ select: [id: string]; refresh: []; delete: [id: string] }>()
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
      <div v-if="!tasks.length" class="empty small">{{ loading ? '正在读取任务…' : '暂无任务，请在右侧创建。' }}</div>
      <div v-for="item in tasks" :key="item.task_id" class="task-card"
        :class="{ selected: item.task_id === selectedId }">
        <button type="button" class="task-select"
          :aria-current="item.task_id === selectedId ? 'true' : undefined"
          :disabled="item.task_id === deletingId" @click="$emit('select', item.task_id)">
          <strong :title="item.task_id">{{ item.task_id }}</strong>
          <span class="status" :class="item.status">{{ statusLabel(item.status) }}</span>
        </button>
        <button type="button" class="task-delete" :disabled="!!deletingId"
          :aria-label="`永久删除任务 ${item.task_id}`" @click="$emit('delete', item.task_id)">
          {{ item.task_id === deletingId ? '删除中…' : '删除' }}
        </button>
      </div>
    </div>
  </aside>
</template>
