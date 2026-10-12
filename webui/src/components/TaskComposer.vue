<script setup lang="ts">
import { ref } from 'vue'
import { atticalPrompt } from '../templates/attical'
defineProps<{ creating: boolean; error: string }>()
const emit = defineEmits<{ submit: [id: string, prompt: string] }>()
const taskId = ref('')
const prompt = ref(atticalPrompt)
function submit() { if (taskId.value.trim() && prompt.value.trim()) emit('submit', taskId.value.trim(), prompt.value) }
</script>
<template>
  <form class="composer" @submit.prevent="submit">
    <div class="composer-title">
      <h2>新建任务</h2>
      <button type="button" class="text-button" :disabled="creating" @click="prompt = atticalPrompt">恢复 AttiCal 模板</button>
    </div>
    <div class="composer-fields">
      <label class="id-field">任务 ID
        <input
          v-model="taskId" placeholder="例如 attical-check-01" pattern="[a-zA-Z0-9][a-zA-Z0-9_-]*"
          maxlength="64" required :disabled="creating" autocomplete="off"
        />
        <span class="muted">字母、数字、下划线、短横线；ID 不可复用</span>
      </label>
      <label class="prompt-field">验证提示词
        <textarea v-model="prompt" rows="10" required :disabled="creating" placeholder="描述验证目标与约束…"></textarea>
      </label>
    </div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div class="composer-footer">
      <span>&lt;task_id&gt; 自动替换为任务 ID</span>
      <button type="submit" class="primary-button" :disabled="creating || !taskId.trim() || !prompt.trim()">{{ creating ? '创建中…' : '创建任务' }}</button>
    </div>
  </form>
</template>
