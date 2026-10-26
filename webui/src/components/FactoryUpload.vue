<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { uploadToFactory } from '../api'
import type { Task } from '../types'

const props = defineProps<{ task: Task | null; disabled: boolean }>()
const busy = ref(false)
const error = ref('')
const uploaded = ref<boolean | null>(null)
const lastFailed = computed(() => uploaded.value === null ? props.task?.keti5_upload_failed : !uploaded.value)
watch(() => props.task?.task_id, () => { error.value = ''; uploaded.value = null })
async function upload() {
  const task = props.task
  if (busy.value || props.disabled || !task?.keti5) return
  // 会话暂停或 idle 不代表业务结束，以验证状态优先。
  const ended = ['failed', 'cancelled', 'completed'].includes(task.verification_status || task.status)
  if (!ended && !window.confirm('当前上传的是中间结果而非完整结果，是否上传。')) return
  busy.value = true
  error.value = ''
  try {
    await uploadToFactory(task.task_id)
    if (props.task?.task_id === task.task_id) uploaded.value = true
  } catch (cause) {
    if (props.task?.task_id === task.task_id) {
      uploaded.value = false
      error.value = cause instanceof Error ? cause.message : String(cause)
    }
  } finally { busy.value = false }
}
</script>
<template>
  <button type="button" :disabled="disabled || !task?.keti5 || busy" :aria-busy="busy" @click="upload">
    {{ busy ? '上传中…' : '上传到工厂' }}
  </button>
  <pre v-if="error" class="project-error factory-upload-error" role="alert" tabindex="0" aria-label="工厂上传错误详情">{{ error }}</pre>
  <p v-else-if="lastFailed != null" class="project-hint" role="status">最近上传：{{ lastFailed ? '失败' : '成功' }}</p>
</template>
<style scoped>
.factory-upload-error {
  box-sizing: border-box;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  max-height: 20rem;
  flex-shrink: 0;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: normal;
  font: inherit;
}
</style>
