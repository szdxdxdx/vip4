<script setup lang="ts">
import { ref } from 'vue'

const taskId = ref('')
const text = ref('')
const sending = ref(false)
const reply = ref('')

async function send() {
  const id = taskId.value.trim()
  if (!id || !text.value.trim() || sending.value) return
  sending.value = true
  reply.value = ''
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined
  try {
    const response = await fetch('/task/create_task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: id, prompt: text.value }),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(typeof data.detail === 'string' ? data.detail : '请检查任务 ID 和提示词')
    }
    await response.json()
    const events = await fetch(`/task/get_events?task_id=${encodeURIComponent(id)}`, {
      headers: { Accept: 'application/x-ndjson' },
    })
    if (!events.ok) {
      const data = await events.json()
      throw new Error(typeof data.detail === 'string' ? data.detail : '读取回复失败，请重试')
    }
    if (!events.body) throw new Error('读取回复失败，请重试')
    reader = events.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let settled = false
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let newline: number
      while ((newline = buffer.indexOf('\n')) !== -1) {
        const taskEvent = JSON.parse(buffer.slice(0, newline))
        buffer = buffer.slice(newline + 1)
        if (taskEvent.type === 'error') throw new Error(taskEvent.error)
        if (taskEvent.type !== 'agent') continue
        const event = taskEvent.data
        if (event.type === 'error') throw new Error(event.error)
        if (event.type === 'message_start' && event.message.role === 'assistant') reply.value = ''
        if (event.type === 'message_update' && event.assistantMessageEvent.type === 'text_delta') {
          reply.value += event.assistantMessageEvent.delta
        }
        if (event.type === 'message_end' && event.message.role === 'assistant') {
          reply.value = event.message.content
            .filter((block: { type: string }) => block.type === 'text')
            .map((block: { text: string }) => block.text).join('')
        }
        if (event.type === 'agent_settled') settled = true
      }
      if (done) break
    }
    if (!settled) throw new Error('回复连接中断，请重试')
    text.value = ''
  } catch (error) {
    reply.value += '\n' + (error instanceof Error ? error.message : '发送失败，请重试')
  } finally {
    await reader?.cancel().catch(() => {})
    reader?.releaseLock()
    sending.value = false
  }
}
</script>

<template>
  <form @submit.prevent="send">
    <input v-model="taskId" aria-label="任务 ID" placeholder="task_id" pattern="[a-zA-Z0-9][a-zA-Z0-9_-]*" maxlength="64" required :disabled="sending" />
    <textarea v-model="text" aria-label="对话内容" placeholder="输入对话内容" :disabled="sending" />
    <button type="submit" :disabled="sending || !taskId.trim() || !text.trim()">{{ sending ? '发送中…' : '发送' }}</button>
  </form>
  <p style="white-space: pre-wrap">{{ reply }}</p>
</template>
