<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { Artifact } from '../types'
import { fileUrl } from '../api'
const props = defineProps<{ taskId: string; files: Artifact[]; loading: boolean; error: string }>()
defineEmits<{ refresh: [] }>()
const tab = ref<'preview' | 'files'>('preview')
const selectedReport = ref('')
const previewLoading = ref(false)
const reportDialog = ref<HTMLDialogElement>()
const expanded = ref(false)
function closeReport() {
  reportDialog.value?.close()
  expanded.value = false
}
async function expandReport() {
  if (!selectedReport.value) return
  expanded.value = true
  await nextTick()
  if (expanded.value) reportDialog.value?.showModal()
}
const reports = computed(() => props.files.filter(f => f.kind === 'report_html'))
watch(() => props.taskId, () => { closeReport(); selectedReport.value = ''; tab.value = 'preview'; previewLoading.value = false }, { flush: 'sync' })
watch(reports, value => {
  if (!value.some(f => f.path === selectedReport.value)) selectedReport.value = value[0]?.path || ''
}, { immediate: true })
watch(selectedReport, path => { closeReport(); previewLoading.value = !!path })
function size(bytes: number) { return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB` }
</script>
<template>
  <aside class="panel artifacts" aria-label="报告与文件">
    <div class="panel-heading"><div><span class="eyebrow">ARTIFACTS</span><h2>报告与文件</h2></div><button class="icon-button" :disabled="!taskId || loading" @click="$emit('refresh')" aria-label="刷新报告与文件">刷新</button></div>
    <div class="tabs" role="tablist" aria-label="产物视图"><button id="preview-tab" role="tab" :aria-selected="tab === 'preview'" aria-controls="artifact-view" :class="{ active: tab === 'preview' }" @click="tab = 'preview'">报告预览 <span>{{ reports.length }}</span></button><button id="files-tab" role="tab" :aria-selected="tab === 'files'" aria-controls="artifact-view" :class="{ active: tab === 'files' }" @click="tab = 'files'">下载文件 <span>{{ files.length }}</span></button></div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div id="artifact-view" class="artifact-view" role="tabpanel" :aria-labelledby="tab === 'preview' ? 'preview-tab' : 'files-tab'" :aria-busy="loading">
      <div v-if="loading" class="empty small">正在读取产物…</div>
      <template v-else-if="tab === 'preview'">
        <div v-if="!reports.length" class="empty"><div class="empty-symbol">▤</div><h3>报告尚未生成</h3><p>完成验证后，真实 HTML 报告将在此预览。</p><p class="muted">仅展示 API 返回的 workspace 文件</p></div>
        <template v-else><div class="report-toolbar"><label>选择报告<select v-model="selectedReport"><option v-for="file in reports" :key="file.path" :value="file.path">{{ file.path }}</option></select></label><div class="report-actions"><button type="button" class="icon-button" @click="expandReport" aria-haspopup="dialog">展开报告 ⤢</button><a class="download-link" :href="fileUrl(taskId, selectedReport, true)">下载 HTML</a></div></div><p v-if="previewLoading" class="preview-loading">报告加载中…</p><iframe :key="taskId + selectedReport" :src="fileUrl(taskId, selectedReport)" sandbox="allow-scripts" :title="`报告预览：${selectedReport}`" @load="previewLoading = false"></iframe><p class="preview-note">隔离预览 · 如无法展示，请下载 HTML 查看</p></template>
      </template>
      <template v-else><div v-if="!files.length" class="empty small">暂无可下载文件</div><ul v-else class="file-list"><li v-for="file in files" :key="file.path"><div><span class="file-kind">{{ file.kind === 'report_html' ? 'HTML 报告' : file.kind === 'report_json' ? 'JSON 报告' : '工作文件' }}</span><strong>{{ file.path }}</strong><span class="muted">{{ size(file.size) }}</span></div><a :href="fileUrl(taskId, file.path, true)" :aria-label="`下载 ${file.path}`">下载</a></li></ul></template>
    </div>
    <dialog ref="reportDialog" class="report-dialog" aria-labelledby="expanded-report-title" @close="expanded = false" @cancel="expanded = false" @click="event => { if (event.target === reportDialog) closeReport() }">
      <div v-if="expanded" class="expanded-report">
        <div class="expanded-report-header">
          <div><h2 id="expanded-report-title">报告阅读</h2><p>{{ taskId }} / {{ selectedReport }}</p></div>
          <a class="download-link" :href="fileUrl(taskId, selectedReport, true)">下载 HTML</a>
          <button type="button" class="icon-button" autofocus @click="closeReport" aria-label="关闭展开报告">关闭 ✕</button>
        </div>
        <iframe :key="taskId + selectedReport" :src="fileUrl(taskId, selectedReport)" sandbox="allow-scripts" :title="`展开报告：${selectedReport}`"></iframe>
      </div>
    </dialog>
  </aside>
</template>
