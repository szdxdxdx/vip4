<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, Task } from '../types'
import { statusLabel } from '../types'
const props = defineProps<{
  task: Task | null; selectedId: string; messages: ChatMessage[]
  streamState: string; loading: boolean; error: string
}>()
const tools = computed(() => props.messages.filter(message => message.kind === 'tool'))
const counts = computed(() => ({
  total: tools.value.length,
  running: tools.value.filter(tool => tool.state === 'running').length,
  success: tools.value.filter(tool => tool.state === 'success').length,
  failed: tools.value.filter(tool => tool.state === 'error').length,
}))
const streamLabels: Record<string, string> = {
  idle: '未连接', connecting: '连接 / 等待输出', live: '接收事件中', closed: '流已关闭', error: '连接异常',
}
const toolLabels = { running: '运行中', success: '成功', error: '失败' }
</script>
<template>
  <section class="progress-panel" aria-label="进度预览">
    <div class="panel-heading"><h2>进度预览</h2></div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div class="progress-scroll" :aria-busy="loading">
      <div v-if="!selectedId" class="empty small">请选择任务</div>
      <template v-else>
        <dl class="progress-summary">
          <div><dt>任务 ID</dt><dd>{{ selectedId }}</dd></div>
          <div><dt>任务状态</dt><dd>{{ task ? statusLabel(task.status) : loading ? '加载中' : '未知' }}</dd></div>
          <div><dt>连接状态</dt><dd>{{ streamLabels[streamState] || streamState }}</dd></div>
          <div><dt>工具总数</dt><dd>{{ counts.total }}</dd></div>
          <div><dt>运行</dt><dd>{{ counts.running }}</dd></div>
          <div><dt>成功</dt><dd>{{ counts.success }}</dd></div>
          <div><dt>失败</dt><dd>{{ counts.failed }}</dd></div>
        </dl>
        <p class="muted">仅统计已接收的工具调用；工具成功不代表 IP 验证通过，验证结论请查看报告。</p>
        <h3 class="progress-list-title">工具调用</h3>
        <p v-if="!tools.length" class="empty small">暂无工具调用</p>
        <ul v-else class="progress-tools">
          <li v-for="tool in tools" :key="tool.id">
            <div><strong>{{ tool.toolName || '工具' }}</strong><span class="muted">{{ tool.toolCallId }}</span></div>
            <span class="status" :class="tool.state">{{ tool.state ? toolLabels[tool.state] : '未知' }}</span>
          </li>
        </ul>
      </template>
    </div>
  </section>
</template>
