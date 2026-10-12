<script setup lang="ts">
import type { Task } from '../types'
import { statusLabel } from '../types'
defineProps<{ tasks: Task[]; selectedId: string; loading: boolean; error: string }>()
defineEmits<{ select: [id: string]; refresh: [] }>()
</script>
<template>
  <aside class="panel sidebar" aria-label="任务列表">
    <div class="panel-heading">
      <h2>任务列表 <span class="count">{{ tasks.length }}</span></h2>
      <button class="icon-button" :disabled="loading" @click="$emit('refresh')" aria-label="刷新任务列表">{{ loading ? '加载中' : '刷新' }}</button>
    </div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div class="task-list" :aria-busy="loading">
      <div v-if="!tasks.length" class="empty small">{{ loading ? '正在读取任务…' : '暂无任务，请在右侧创建。' }}</div>
      <button
        v-for="item in tasks" :key="item.task_id" class="task-card"
        :class="{ selected: item.task_id === selectedId }"
        :aria-current="item.task_id === selectedId ? 'true' : undefined"
        @click="$emit('select', item.task_id)"
      >
        <div class="task-row">
          <strong>{{ item.task_id }}</strong>
          <span class="status" :class="item.status">{{ statusLabel(item.status) }}</span>
        </div>
      </button>
    </div>
  </aside>
</template>
