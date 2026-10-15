<script setup lang="ts">
import { onMounted, ref } from 'vue'

const content = ref('')
const error = ref('')
const status = ref('')
const saving = ref(false)

async function load() {
  try {
    const response = await fetch('/api/config/pi-models')
    if (!response.ok) throw new Error('读取失败')
    content.value = (await response.json()).content
  } catch (err) { error.value = err instanceof Error ? err.message : String(err) }
}
async function save() {
  saving.value = true
  error.value = ''
  status.value = ''
  try {
    const response = await fetch('/api/config/pi-models', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content.value }),
    })
    if (!response.ok) throw new Error('保存失败')
    status.value = '已保存'
  } catch (err) { error.value = err instanceof Error ? err.message : String(err) }
  finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <main class="config-page">
    <header class="config-heading"><h1>Pi 模型配置</h1><button type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button></header>
    <textarea v-model="content" spellcheck="false" aria-label="models.json 内容" />
    <p v-if="status" class="config-status">{{ status }}</p>
    <p v-if="error" class="config-error">{{ error }}</p>
  </main>
</template>
