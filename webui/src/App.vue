<script setup lang="ts">
import { ref } from 'vue'

const taskId = ref('')
const text = ref(`请使用 SKILL verify-ip，使用 CBMC，按 skill 的完整 workflow 执行本次软件 IP 验证测试。

指定 IP：AttiCal。
<ip> = AttiCal。
<input>/ = /app/vip4/dataset/16-ip/，输入数据只读。
头文件搜索路径：<input>/include/。
待验证 IP 形式模型：<input>/ip/AttiCal/formal_model/*.tex。
待验证 IP 代码：<input>/ip/AttiCal/implementation/*.c、*.h。
请将 <input> 替换为上述实际路径。
唯一输出目录（workspace）：/app/vip4/tasks/<task_id>/workspace/。所有生成文件、临时文件、验证产物和报告只能写入此 workspace。
允许读取 /app/vip4/skills/ 下 verify-ip skill 及其 reference/scripts，允许调用必要工具。skill .venv 依赖由后台预备，无需安装或修改全局环境。禁止读取或复用其他历史任务的套件、驱动、结果或报告，不得修改输入数据、skill 或 workspace 之外的文件。

本次是模拟/演示，但必须真实使用 skill 的 run_cbmc.py 执行且仅执行一个 case，不需要全 case 验证。请先阅读 skill，再按完整 workflow 完成：规约/实现分析与 IR、suite、所选 case 的 driver/config、run_cbmc.py 实际运行与结果分析、conclusion/experience，最后调用 make_report 生成最终 report.html 和 report.json（均保存于 workspace 内，具体结构遵循 skill）。
报告中清楚列出实际运行的唯一 case、证据和真实结果；所有未运行 case 必须明确标为未验证，禁止捏造结果，禁止宣称整个 IP 或全部 case 已通过。以最终 report.html/report.json 展示验证结果，不用会话回复代替报告。

无工具调用次数限制，请一轮完整执行，不要中途等待确认。完成最终报告后，会话只回复【任务已完成】。`)
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
      body: JSON.stringify({ task_id: id, prompt: text.value.replaceAll('<task_id>', id) }),
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
    <textarea v-model="text" rows="18" aria-label="验证提示词（可编辑）" placeholder="输入验证提示词" :disabled="sending" />
    <button type="submit" :disabled="sending || !taskId.trim() || !text.trim()">{{ sending ? '发送中…' : '发送' }}</button>
  </form>
  <p style="white-space: pre-wrap">{{ reply }}</p>
</template>
