<script setup lang="ts">
import { onMounted, ref } from 'vue'

const keys = ['KETI2_BASE_URL', 'KETI3_BASE_URL', 'KETI5_CALLBACK_URL', 'KETI5_UPLOAD_URL', 'KETI5_JENKINS_USER', 'KETI5_JENKINS_API_TOKEN'] as const
const values = ref<Record<string, string>>({})
const loaded = ref(false)
const busy = ref(false)
const message = ref('')
const error = ref('')

async function request(save = false) {
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    const response = await fetch('/api/config/keti-ip', save ? {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values.value),
    } : undefined)
    if (!response.ok) throw new Error(`${save ? '保存' : '读取'}失败（HTTP ${response.status}）`)
    if (save) message.value = '已保存并生效'
    else { values.value = await response.json(); loaded.value = true }
  } catch (err) { error.value = err instanceof Error ? err.message : String(err) }
  finally { busy.value = false }
}
onMounted(() => request())
</script>

<template>
  <main class="config-page keti-config">
    <header class="config-heading"><h1>课题接口配置</h1><button type="button" :disabled="busy || !loaded" @click="request(true)">保存</button></header>
    <label v-for="key in keys" :key="key">
      {{ key }}
      <input v-model="values[key]" type="text" :disabled="busy || !loaded" spellcheck="false" autocomplete="off" />
    </label>
    <p role="status">{{ message }}</p>
    <p v-if="error" class="config-error" role="alert">{{ error }}</p>
  </main>
</template>

<style scoped>
.keti-config { overflow:auto }
label { display:flex; flex-direction:column; gap:6px }
input { padding:8px; border:1px solid var(--line); border-radius:0; background:#fff; color:inherit }
</style>
