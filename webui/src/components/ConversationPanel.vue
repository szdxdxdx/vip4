<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage, Task } from '../types'
import { ipLabel, statusLabel } from '../types'
import MessageItem from './MessageItem.vue'
const props = defineProps<{ task: Task | null; selectedId: string; messages: ChatMessage[]; loading: boolean; error: string; streamError: string; streamState: string; active: boolean; draft: string; chatBusy: string; chatError: string; canSend: boolean; canPause: boolean; deleting: boolean }>()
defineEmits<{ replay: []; send: []; pause: []; 'update:draft': [value: string] }>()
const scrollArea = ref<HTMLElement>()
const nearBottom = ref(true)
function onScroll() {
  const el = scrollArea.value
  if (el) nearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100
}
async function toBottom() { await nextTick(); const el = scrollArea.value; if (el) el.scrollTop = el.scrollHeight }
watch(() => props.selectedId, () => { nearBottom.value = true; void toBottom() })
watch(() => props.messages, () => { if (props.active && nearBottom.value) void toBottom() }, { deep: true, flush: 'post' })
watch(() => props.active, active => { if (active && nearBottom.value) void toBottom() }, { flush: 'post' })
const streamLabels: Record<string, string> = { idle: '未连接', connecting: '连接 / 等待输出', live: '接收事件中', closed: '流已关闭', error: '连接异常' }
</script>
<template>
  <section class="conversation" aria-label="任务会话">
    <div class="panel-heading">
      <div class="conversation-identity">
        <h2>{{ task ? ipLabel(task) : selectedId || 'Agent 对话' }}</h2>
        <p v-if="selectedId">projectID: {{ task?.projectID || '—' }} / taskID: {{ selectedId }}</p>
      </div>
      <div class="heading-actions">
        <span v-if="task" class="status" :class="task.status">{{ statusLabel(task.status) }}</span>
        <button v-if="selectedId" class="icon-button" :disabled="loading || deleting || !!chatBusy" @click="$emit('replay')">重新加载</button>
      </div>
    </div>
    <div v-if="selectedId" class="connection">
      <span class="connection-dot" :class="streamState"></span>{{ streamLabels[streamState] }}
      <span v-if="task?.verification_status" class="muted">原验证：{{ statusLabel(task.verification_status) }}</span>
    </div>
    <p v-if="error || streamError" class="error-banner" role="alert">{{ error || streamError }}</p>
    <div ref="scrollArea" class="message-scroll" @scroll.passive="onScroll" :aria-busy="loading">
      <div v-if="loading" class="empty"><span class="loader"></span>正在加载任务与历史消息…</div>
      <div v-else-if="!selectedId" class="empty">
        <div class="empty-symbol">✦</div><h3>开始一次验证</h3>
        <p>选择左侧任务查看对话，或在项目验证中提交新任务。</p>
      </div>
      <template v-else>
        <MessageItem v-for="message in messages" :key="message.id" :message="message" />
        <p v-if="!messages.length" class="empty small">未开始</p>
        <p v-if="streamState === 'connecting'" class="waiting">等待 Agent 输出，任务可能仍在准备中…</p>
      </template>
    </div>
    <form class="chat-input" @submit.prevent="$emit('send')">
      <label for="chat-message">继续对话</label>
      <textarea id="chat-message" :value="draft" rows="3" :disabled="!selectedId || deleting"
        placeholder="输入消息；运行中也可发送补充" @input="$emit('update:draft', ($event.target as HTMLTextAreaElement).value)" />
      <p v-if="chatError" class="error-banner" role="alert">{{ chatError }}</p>
      <div class="chat-actions">
        <span class="muted" role="status">{{ chatBusy === 'send' ? '发送中…' : chatBusy === 'pause' ? '等待后端暂停…' : task?.status === 'running' ? '运行中可发送补充' : '发送后在原任务会话继续' }}</span>
        <button type="submit" :disabled="!canSend">发送</button>
        <button type="button" :disabled="!canPause" @click="$emit('pause')">暂停</button>
      </div>
    </form>
    <button v-if="!nearBottom" class="jump-bottom" @click="nearBottom = true; toBottom()">↓ 查看最新消息</button>
  </section>
</template>
