<script setup lang="ts">
import type { ChatMessage } from '../types'
defineProps<{ message: ChatMessage }>()
</script>
<template>
  <article class="message" :class="message.kind">
    <template v-if="message.kind === 'tool'">
      <details class="tool-card" :class="message.state">
        <summary><span class="tool-icon">⌘</span><strong>{{ message.toolName }}</strong><span class="status" :class="message.state">{{ message.state === 'running' ? '执行中' : message.state === 'error' ? '失败' : '成功' }}</span><span class="fold-hint">详情</span></summary>
        <div class="tool-body"><h4>参数</h4><pre>{{ message.args || '无参数' }}</pre><h4>输出</h4><pre>{{ message.output || (message.state === 'running' ? '等待工具输出…' : '无文本输出') }}</pre></div>
      </details>
    </template>
    <template v-else>
      <div class="message-label"><span class="avatar">{{ message.kind === 'user' ? '你' : message.kind === 'error' ? '!' : 'A' }}</span>{{ message.kind === 'user' ? '任务提示词' : message.kind === 'error' ? '执行错误' : 'Agent' }}</div>
      <details v-if="message.kind === 'user'" class="prompt-content"><summary>查看完整任务提示词</summary><pre>{{ message.text }}</pre></details>
      <template v-else><details v-if="message.thinking" class="thinking"><summary>思考过程 · 展开查看</summary><pre>{{ message.thinking }}</pre></details><pre v-if="message.text" class="message-text">{{ message.text }}</pre></template>
    </template>
  </article>
</template>
