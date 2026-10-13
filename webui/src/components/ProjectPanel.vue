<script setup lang="ts">
import { toRef } from 'vue'
import { useProject } from '../composables/useProject'
import { projectLabels, sourceLabels } from '../projectTypes'
const props = defineProps<{ active: boolean }>()
const emit = defineEmits<{ viewTask: [id: string]; forced: [] }>()
const { projectID, source, prompt, progress, results, error, busy, polling, submit, forceSubmit, removeProject, query } = useProject(toRef(props, 'active'), () => emit('forced'))
</script>
<template>
  <main class="project-panel" aria-label="项目验证">
    <section class="panel project-input">
      <h2>项目验证</h2>
      <form @submit.prevent="submit">
        <label for="project-source">输入来源</label>
        <select id="project-source" v-model="source">
          <option value="keti2">课题二（多个IP）</option>
          <option value="keti3">课题三（合成代码单IP）</option>
        </select>
        <p v-if="source === 'keti3'" class="project-hint">按项目 ID 通过 POST /api/verify 打包已有合成产物，下载 ZIP 并使用其中全部文件，构建单个任务（IP 标识 keti3:项目ID），不调用 synthesize。原始 ZIP 保存为任务根目录 keti3.zip；全部文件解压到 input 并保留目录。IR 目录为形式模型，根目录 C/H 为主 IP，iplib 为依赖；缺少 IR 时由 Agent 明确报告缺模型。</p>
        <label for="project-id">项目 ID</label>
        <input id="project-id" v-model="projectID" autocomplete="off" placeholder="输入项目 ID" />
        <label for="project-prompt">提示词（可选）</label>
        <textarea id="project-prompt" v-model="prompt" rows="5" placeholder="留空使用后端默认 CBMC 验证提示词" />
        <p class="project-hint">两来源共用项目 ID；普通提交不覆盖已有项目，强制提交（含切换来源）会永久删除同 ID 全部旧任务。</p>
        <div class="project-actions">
          <button type="submit" :disabled="busy || !projectID.trim()">提交验证</button>
          <button type="button" :disabled="busy || !projectID.trim()" @click="forceSubmit">强制提交验证</button>
          <button type="button" :disabled="busy || !projectID.trim()" @click="query">查询已有项目</button>
          <button type="button" :disabled="busy || !projectID.trim()" @click="removeProject">删除项目</button>
        </div>
      </form>
      <p v-if="error" class="project-error" role="alert">{{ error }}（可手动查询重试）</p>
      <p class="project-hint" role="status">{{ busy ? '请求中…' : polling ? '每 2 秒自动查询' : '自动查询已停止' }}</p>
    </section>
    <section class="panel project-output" aria-label="项目进度与结果">
      <template v-if="progress">
        <div class="project-summary">
          <h2>{{ progress.projectID }}</h2>
          <strong>{{ projectLabels[progress.status] }}</strong>
          <span v-if="progress.source">来源：{{ sourceLabels[progress.source] }}</span>
          <span>已结束 {{ progress.finished }} / 总计 {{ progress.total }}</span>
        </div>
        <p v-if="progress.error" class="project-error">{{ progress.error }}</p>
        <p v-if="!progress.tasks.length" class="project-hint">暂无任务</p>
        <article v-for="task in progress.tasks" :key="task.task_id" class="project-task">
          <div class="project-summary">
            <h3>{{ task.ip_id || '未提供 IP 标识' }}</h3>
            <span>{{ projectLabels[task.status] }}</span>
            <button type="button" @click="emit('viewTask', task.task_id)">查看任务</button>
          </div>
          <p class="project-hint">任务ID：{{ task.task_id }}</p>
          <p v-if="task.created_at" class="project-hint">创建时间：{{ task.created_at }}</p>
          <ul v-if="results?.tasks.find(item => item.task_id === task.task_id)?.files.length" class="project-files">
            <li v-for="file in results?.tasks.find(item => item.task_id === task.task_id)?.files" :key="file.path">
              <a :href="file.download_url" download>{{ file.path }}</a>
              <span>{{ file.kind }} · {{ file.size }} 字节</span>
            </li>
          </ul>
          <p v-else class="project-hint">暂无结果文件</p>
        </article>
      </template>
      <p v-else class="project-hint">提交验证或查询已有项目后显示进度与结果。</p>
    </section>
  </main>
</template>
