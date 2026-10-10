<script setup lang="ts">
import { ref } from 'vue'

const text = ref('')
const sending = ref(false)

async function send() {
  if (!text.value.trim() || sending.value) return
  sending.value = true
  try {
    const response = await fetch('/talk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value }),
    })
    if (!response.ok) throw new Error('发送失败')
    text.value = ''
  } catch {
    alert('发送失败，请重试')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <form @submit.prevent="send">
    <textarea v-model="text" aria-label="对话内容" placeholder="输入对话内容" :disabled="sending" />
    <button type="submit" :disabled="sending || !text.trim()">{{ sending ? '发送中…' : '发送' }}</button>
  </form>
</template>
