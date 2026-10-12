<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { Artifact } from '../types'
import { fileUrl } from '../api'
const props = defineProps<{ taskId: string; files: Artifact[]; loading: boolean; error: string; view: 'report' | 'files' }>()
defineEmits<{ refresh: [] }>()
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
watch(() => props.view, closeReport)
const reports = computed(() => props.files.filter(f => f.kind === 'report_html'))
watch(() => props.taskId, () => { closeReport(); selectedReport.value = ''; previewLoading.value = false }, { flush: 'sync' })
watch(reports, value => {
  if (!value.some(f => f.path === selectedReport.value)) selectedReport.value = value[0]?.path || ''
}, { immediate: true })
watch(selectedReport, path => { closeReport(); previewLoading.value = !!path })
function size(bytes: number) { return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB` }
</script>
<template>
  <section class="artifacts" :aria-label="view === 'report' ? '验证结果报告' : '文件下载'">
    <div class="panel-heading">
      <h2>{{ view === 'report' ? '验证结果报告' : '文件下载' }}</h2>
      <button class="icon-button" :disabled="!taskId || loading" @click="$emit('refresh')" aria-label="刷新报告与文件">刷新</button>
    </div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div class="artifact-view" :aria-busy="loading">
      <div v-if="!taskId" class="empty small">请选择任务</div>
      <div v-else-if="loading" class="empty small">正在读取产物…</div>
      <template v-else-if="view === 'report'">
        <div v-if="!reports.length" class="empty">
          <h3>报告尚未生成</h3><p>任务产出的 HTML 报告将在此预览。</p>
        </div>
        <template v-else>
          <div class="report-toolbar">
            <label>选择报告
              <select v-model="selectedReport">
                <option v-for="file in reports" :key="file.path" :value="file.path">{{ file.path }}</option>
              </select>
            </label>
            <div class="report-actions">
              <button type="button" class="icon-button" @click="expandReport" aria-haspopup="dialog">展开报告 ⤢</button>
              <a class="download-link" :href="fileUrl(taskId, selectedReport, true)">下载 HTML</a>
            </div>
          </div>
          <p v-if="previewLoading" class="preview-loading">报告加载中…</p>
          <iframe
            :key="taskId + selectedReport" :src="fileUrl(taskId, selectedReport)"
            sandbox="allow-scripts" :title="`报告预览：${selectedReport}`" @load="previewLoading = false"
          ></iframe>
          <p class="preview-note">隔离预览 · 如无法展示，请下载 HTML 查看</p>
        </template>
      </template>
      <template v-else>
        <div v-if="!files.length" class="empty small">暂无可下载文件</div>
        <ul v-else class="file-list">
          <li v-for="file in files" :key="file.path">
            <div>
              <span class="file-kind">{{ file.kind === 'report_html' ? 'HTML 报告' : file.kind === 'report_json' ? 'JSON 报告' : '工作文件' }}</span>
              <strong>{{ file.path }}</strong><span class="muted">{{ size(file.size) }}</span>
            </div>
            <a :href="fileUrl(taskId, file.path, true)" :aria-label="`下载 ${file.path}`">下载</a>
          </li>
        </ul>
      </template>
    </div>
    <dialog
      ref="reportDialog" class="report-dialog" aria-labelledby="expanded-report-title"
      @close="expanded = false" @cancel="expanded = false"
      @click="event => { if (event.target === reportDialog) closeReport() }"
    >
      <div v-if="expanded" class="expanded-report">
        <div class="expanded-report-header">
          <div><h2 id="expanded-report-title">报告阅读</h2><p>{{ taskId }} / {{ selectedReport }}</p></div>
          <a class="download-link" :href="fileUrl(taskId, selectedReport, true)">下载 HTML</a>
          <button type="button" class="icon-button" autofocus @click="closeReport" aria-label="关闭展开报告">关闭 ✕</button>
        </div>
        <iframe
          :key="taskId + selectedReport" :src="fileUrl(taskId, selectedReport)"
          sandbox="allow-scripts" :title="`展开报告：${selectedReport}`"
        ></iframe>
      </div>
    </dialog>
  </section>
</template>
