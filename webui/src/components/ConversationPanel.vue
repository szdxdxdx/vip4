<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage, Task } from '../types'
import { statusLabel } from '../types'
import MessageItem from './MessageItem.vue'
const props = defineProps<{ task: Task | null; selectedId: string; messages: ChatMessage[]; loading: boolean; error: string; streamError: string; streamState: string }>()
defineEmits<{ replay: [] }>()
const scrollArea = ref<HTMLElement>()
const nearBottom = ref(true)
function onScroll() {
  const el = scrollArea.value
  if (el) nearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100
}
async function toBottom() { await nextTick(); const el = scrollArea.value; if (el) el.scrollTop = el.scrollHeight }
watch(() => props.selectedId, () => { nearBottom.value = true; void toBottom() })
watch(() => props.messages, () => { if (nearBottom.value) void toBottom() }, { deep: true, flush: 'post' })
const streamLabels: Record<string, string> = { idle: '未连接', connecting: '连接 / 等待输出', live: '接收事件中', closed: '流已关闭', error: '连接异常' }
</script>
<template>
  <section class="conversation" aria-label="任务会话">
    <div class="panel-heading"><div><span class="eyebrow">CONVERSATION</span><h2>{{ selectedId || 'Agent 对话' }}</h2></div><div class="heading-actions"><span v-if="task" class="status" :class="task.status">{{ statusLabel(task.status) }}</span><button v-if="selectedId" class="icon-button" :disabled="loading" @click="$emit('replay')">重新加载</button></div></div>
    <div v-if="selectedId" class="connection"><span class="connection-dot" :class="streamState"></span>{{ streamLabels[streamState] }}<span>状态以任务元数据为准</span></div>
    <p v-if="error || streamError" class="error-banner" role="alert">{{ error || streamError }}</p>
    <div ref="scrollArea" class="message-scroll" @scroll.passive="onScroll" :aria-busy="loading">
      <div v-if="loading" class="empty"><span class="loader"></span>正在加载任务与历史消息…</div>
      <div v-else-if="!selectedId" class="empty"><div class="empty-symbol">✦</div><h3>开始一次验证</h3><p>选择已有任务回放，或填写任务 ID 创建新任务。</p><p class="muted">消息、工具执行与验证产物将在这里实时呈现。</p></div>
      <template v-else><MessageItem v-for="message in messages" :key="message.id" :message="message" /><p v-if="!messages.length" class="empty small">暂无历史消息</p><p v-if="streamState === 'connecting'" class="waiting">等待 Agent 输出，任务可能仍在准备中…</p></template>
    </div>
    <button v-if="!nearBottom" class="jump-bottom" @click="nearBottom = true; toBottom()">↓ 查看最新消息</button>
  </section>
</template>
