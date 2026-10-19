<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useProject } from '../composables/useProject'
import { atticalPrompt } from '../templates/attical'
import { taskStatusLabel } from '../types'
const props = defineProps<{ active: boolean }>()
const emit = defineEmits<{ viewTask: [id: string]; changed: [] }>()
const { keti5, messages, source, projectID, ip, tool, prompt, dataset, tasks, queryID, queryTaskID, busy,
  loading, submit, refresh } = useProject(toRef(props, 'active'), () => emit('changed'))
const valid = computed(() => source.value === 'local' ? !!ip.value : !!projectID.value.trim())
</script>
<template>
  <main class="project-panel" aria-label="项目验证">
    <section class="panel project-input">
      <h2>提交验证</h2>
      <form @submit.prevent="submit">
        <label for="project-source">类别</label>
        <select id="project-source" v-model="source">
          <option value="local">local · 本地数据集</option>
          <option value="keti2">keti2 · 课题二</option>
          <option value="keti3">keti3 · 课题三</option>
        </select>
        <template v-if="source === 'local'">
          <label for="dataset-ip">数据集 IP</label>
          <select id="dataset-ip" v-model="ip">
            <option value="" disabled>请选择 IP</option>
            <option v-for="item in dataset" :key="item" :value="item">{{ item }}</option>
          </select>
        </template>
        <template v-else>
          <label for="project-id">项目 ID</label>
          <input id="project-id" v-model="projectID" :readonly="!!keti5" autocomplete="off" placeholder="输入 projectID" />
        </template>
        <label for="verify-tool">验证工具</label>
        <select id="verify-tool" v-model="tool">
          <option value="CBMC">CBMC</option><option value="CPAchecker">CPAchecker</option><option value="KLEE">KLEE</option>
        </select>
        <div class="prompt-label"><label for="project-prompt">提示词（可选，最高优先级）</label></div>
        <textarea id="project-prompt" v-model="prompt" rows="8" placeholder="可留空，使用默认验证流程" />
        <button type="button" class="text-button template-hint" @click="prompt = atticalPrompt">点击填入 AttiCal / CBMC 单 case 演示模板</button>
        <div class="project-actions">
          <button type="submit" :disabled="busy || !valid">提交验证</button>
        </div>
      </form>
    </section>
    <section class="panel project-output" aria-label="全部验证任务">
      <div class="task-table-heading"><h2>全部任务</h2><span class="project-hint">{{ tasks.length }} 条</span></div>
      <form class="task-query" @submit.prevent="refresh">
        <input v-model="queryID" aria-label="查询项目 ID" placeholder="projectID" />
        <input v-model="queryTaskID" aria-label="查询任务 ID" placeholder="taskID（可选）" />
        <button type="submit" :disabled="loading">查询</button>
        <button type="button" :disabled="loading" @click="queryID = ''; queryTaskID = ''; refresh()">全部</button>
      </form>
      <div class="task-table-scroll" :aria-busy="loading">
        <table class="task-table">
          <thead><tr><th>taskID</th><th>projectID</th><th>IP 名字</th><th>验证情况</th><th title="UTC">时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.task_id">
              <td>{{ task.task_id }}</td>
              <td :title="task.projectID || '—'"><span v-if="task.keti" class="source-tag">{{ task.keti }}</span>{{ task.projectID || '—' }}</td>
              <td :title="task.ip_name || task.ip_id || '—'">{{ task.ip_name || task.ip_id || '—' }}</td>
              <td>{{ task.missing_directory ? '实际目录已删除' : task.data_missing ? '任务数据缺失' : taskStatusLabel(task) }}</td>
              <td>{{ task.timestamp || '—' }}</td>
              <td><button type="button" :disabled="task.missing_directory" @click="emit('viewTask', task.task_id)">查看详情</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!tasks.length" class="empty small">{{ loading ? '正在读取任务…' : '请手动刷新查询' }}</p>
      </div>
      <section v-if="messages.length" class="project-messages" aria-labelledby="project-messages-title">
        <h3 id="project-messages-title">消息</h3>
        <p v-for="message in messages" :key="message.id" :class="message.error ? 'project-error' : 'project-hint'" :role="message.error ? 'alert' : 'status'">{{ message.text }}</p>
      </section>
    </section>
  </main>
</template>
