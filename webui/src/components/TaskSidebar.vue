<script setup lang="ts">
import type { Task } from '../types'
import { statusLabel } from '../types'
defineProps<{ tasks: Task[]; selectedId: string; loading: boolean; error: string }>()
defineEmits<{ select: [id: string]; refresh: [] }>()
function date(value: string) {
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>
<template>
  <aside class="panel sidebar" aria-label="任务列表">
    <div class="panel-heading"><div><span class="eyebrow">TASKS</span><h2>任务列表 <span class="count">{{ tasks.length }}</span></h2></div><button class="icon-button" :disabled="loading" @click="$emit('refresh')" aria-label="刷新任务列表">{{ loading ? '加载中' : '刷新' }}</button></div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div class="task-list" :aria-busy="loading">
      <div v-if="!tasks.length" class="empty small">{{ loading ? '正在读取任务…' : '暂无任务，在下方表单创建第一个任务。' }}</div>
      <button v-for="item in tasks" :key="item.task_id" class="task-card" :class="{ selected: item.task_id === selectedId }" :aria-current="item.task_id === selectedId ? 'true' : undefined" @click="$emit('select', item.task_id)">
        <div class="task-row"><strong>{{ item.task_id }}</strong><span class="status" :class="item.status">{{ statusLabel(item.status) }}</span></div>
        <p>{{ item.prompt || '无提示词' }}</p><time>{{ date(item.created_at) }}</time>
      </button>
    </div>
    <div class="sidebar-foot">切换任务仅切换订阅<br>后台验证不会停止</div>
  </aside>
</template>
