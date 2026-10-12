import assert from 'node:assert/strict'
import { test, after } from 'node:test'
import { mkdtemp, readFile, writeFile, mkdir, rm } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'
import { createRenderer, nextTick } from 'vue'

// Compile the actual TS modules to a disposable directory, no testing dependency needed.
const root = resolve(import.meta.dirname, '..')
await mkdir(resolve(root, 'node_modules/.tmp'), { recursive: true })
const out = await mkdtemp(resolve(root, 'node_modules/.tmp/workbench-test-'))
for (const file of ['types.ts', 'api.ts', 'composables/eventReducer.ts', 'composables/useWorkbench.ts']) {
  const source = await readFile(resolve(root, 'src', file), 'utf8')
  let code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
  code = code.replace(/from '(\.[^']+)'/g, "from '$1.js'")
  const destination = resolve(out, file.replace(/\.ts$/, '.js'))
  await mkdir(dirname(destination), { recursive: true })
  await writeFile(destination, code)
}
const { applyTaskEvent, initialConversation } = await import(pathToFileURL(resolve(out, 'composables/eventReducer.js')))
const api = await import(pathToFileURL(resolve(out, 'api.js')))
const { useWorkbench } = await import(pathToFileURL(resolve(out, 'composables/useWorkbench.js')))
const originalFetch = globalThis.fetch
const rpc = data => ({ type: 'agent', data })
const assistant = (text, thinking = '') => ({ role: 'assistant', content: [{ type: 'text', text }, { type: 'thinking', thinking }] })
const response = data => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } })
const waitFor = async predicate => {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await new Promise(r => setTimeout(r, 5)) }
  assert.fail('等待状态超时')
}
after(async () => { globalThis.fetch = originalFetch; await rm(out, { recursive: true, force: true }) })

test('metadata prompt appears once; cumulative snapshots replace deltas; thinking stays plaintext', () => {
  const state = initialConversation('原始提示词')
  applyTaskEvent(state, rpc({ type: 'message_start', message: { role: 'user', content: '原始提示词' } }))
  applyTaskEvent(state, rpc({ type: 'message_end', message: { role: 'user', content: '原始提示词' } }))
  applyTaskEvent(state, rpc({ type: 'agent_start' }))
  applyTaskEvent(state, rpc({ type: 'response', success: true }))
  applyTaskEvent(state, rpc({ type: 'message_start', message: assistant('前缀') }))
  applyTaskEvent(state, rpc({ type: 'message_update', assistantMessageEvent: { type: 'text_delta', delta: '增量' } }))
  applyTaskEvent(state, rpc({ type: 'message_update', assistantMessageEvent: { type: 'thinking_delta', delta: '<script>思考</script>' } }))
  assert.equal(state.items[1].text, '前缀增量')
  assert.equal(state.items[1].thinking, '<script>思考</script>')
  applyTaskEvent(state, rpc({ type: 'message_end', message: assistant('最终内容', '最终思考') }))
  assert.equal(state.items[1].text, '最终内容')
  assert.equal(state.items[1].thinking, '最终思考')
  assert.equal(state.items.length, 2)
  applyTaskEvent(state, rpc({ type: 'message_start', message: assistant('下一条') }))
  assert.equal(state.items.length, 3)
})

test('tools update by toolCallId, truncate large output and distinguish failure', () => {
  const state = initialConversation()
  applyTaskEvent(state, rpc({ type: 'tool_execution_start', toolCallId: 'a', toolName: 'bash', args: { command: 'echo ok' } }))
  applyTaskEvent(state, rpc({ type: 'tool_execution_start', toolCallId: 'b', toolName: 'read' }))
  applyTaskEvent(state, rpc({ type: 'tool_execution_update', toolCallId: 'a', partialResult: { content: [{ type: 'text', text: 'partial' }] } }))
  assert.equal(state.items[0].output, 'partial')
  applyTaskEvent(state, rpc({ type: 'tool_execution_end', toolCallId: 'a', result: { content: [{ type: 'text', text: 'x'.repeat(50000) }] }, isError: true }))
  applyTaskEvent(state, rpc({ type: 'tool_execution_end', toolCallId: 'b', result: 'ok', isError: false }))
  assert.equal(state.items.length, 2)
  assert.equal(state.items[0].state, 'error')
  assert.match(state.items[0].args, /echo ok/)
  assert.ok(state.items[0].output.length < 24100)
  assert.match(state.items[0].output, /截断/)
  assert.equal(state.items[1].state, 'success')
  applyTaskEvent(state, { type: 'error', error: '顶层任务错误' })
  assert.equal(state.items[2].kind, 'error')
})

test('NDJSON handles split UTF-8, blank lines and final line without newline', async () => {
  const bytes = new TextEncoder().encode('\n' + JSON.stringify(rpc({ type: 'message_start', message: assistant('中文') })) + '\n' + JSON.stringify({ type: 'error', error: '错误' }))
  globalThis.fetch = async () => new Response(new ReadableStream({ start(c) {
    for (let i = 0; i < bytes.length; i += 7) c.enqueue(bytes.slice(i, i + 7))
    c.close()
  } }))
  const events = []
  await api.streamTask('含 空格', new AbortController().signal, e => events.push(e))
  assert.equal(events.length, 2)
  assert.equal(events[0].data.message.content[0].text, '中文')
  assert.equal(events[1].error, '错误')
})

test('API paths are encoded, create body matches contract, HTTP detail is surfaced', async () => {
  assert.equal(api.fileUrl('a b', 'reports/a #中.html', true), '/task/get_file?task_id=a%20b&path=reports%2Fa%20%23%E4%B8%AD.html&download=true')
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/task/create_task')
    assert.deepEqual(JSON.parse(options.body), { task_id: 'manual-id', prompt: 'prompt' })
    return response({ task_id: 'manual-id', status: 'created' })
  }
  await api.createTask('manual-id', 'prompt')
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: '任务已存在' }), { status: 409 })
  await assert.rejects(api.createTask('manual-id', 'prompt'), /任务已存在/)
  globalThis.fetch = async () => new Response('not json\n')
  await assert.rejects(api.streamTask('x', new AbortController().signal, () => {}), /事件流解析失败/)
})

const renderer = createRenderer({
  createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
  insert() {}, remove() {}, setText() {}, setElementText() {}, parentNode: () => null,
  nextSibling: () => null, patchProp() {},
})
function mountedWorkbench() {
  let workbench
  const app = renderer.createApp({ setup() { workbench = useWorkbench(); return () => null } })
  app.mount({})
  return { app, w: workbench }
}

test('initial selection, A→B switch aborts old subscription; no cross-talk or duplicate prompt', async () => {
  const streams = new Map()
  const detail = id => ({ task: { task_id: id, prompt: `prompt-${id}`, status: 'running', created_at: '' }, files: [{ path: `${id}/report.html`, kind: 'report_html', size: 20 }] })
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_tasks') return response({ tasks: [detail('A').task, detail('B').task] })
    const id = new URL(url, 'http://local').searchParams.get('task_id')
    if (url.startsWith('/task/get_task')) return response(detail(id))
    return new Response(new ReadableStream({ start(c) { streams.set(id, { c, signal: options.signal }) } }))
  }
  const { app, w } = mountedWorkbench()
  try {
    await w.initialize()
    await waitFor(() => streams.has('A'))
    assert.equal(w.selectedId.value, 'A')
    const selectingB = w.selectTask('B')
    await waitFor(() => streams.has('B'))
    assert.equal(streams.get('A').signal.aborted, true)
    // Simulate a late old event even when a transport doesn't immediately abort read().
    const send = (id, text) => streams.get(id).c.enqueue(new TextEncoder().encode(JSON.stringify(rpc({ type: 'message_start', message: assistant(text) })) + '\n'))
    send('A', '过期的 A 输出')
    send('B', 'B 输出')
    await waitFor(() => w.messages.value.length === 2)
    assert.deepEqual(w.messages.value.map(m => m.text), ['prompt-B', 'B 输出'])
    assert.equal(w.files.value[0].path, 'B/report.html')
    app.unmount()
    streams.get('B').c.close()
    await selectingB
    await nextTick()
  } finally { app.unmount() }
})

test('closed stream retries metadata race; uses final metadata status and files', async () => {
  let reads = 0
  let listReads = 0
  globalThis.fetch = async url => {
    if (url === '/task/list_tasks') { listReads++; return response({ tasks: [] }) }
    if (url.startsWith('/task/get_task')) {
      reads++
      return response({ task: { task_id: 'demo', prompt: 'demo prompt', status: reads < 3 ? 'running' : 'completed', created_at: '' }, files: reads < 3 ? [] : [{ path: 'report.html', kind: 'report_html', size: 30 }] })
    }
    return new Response(JSON.stringify(rpc({ type: 'agent_settled' })) + '\n')
  }
  const { app, w } = mountedWorkbench()
  try {
    await w.selectTask('demo')
    assert.equal(w.streamState.value, 'closed')
    assert.equal(w.task.value.status, 'completed')
    assert.equal(w.files.value[0].path, 'report.html')
    assert.ok(listReads >= 2)
    assert.equal(w.messages.value.length, 1)
  } finally { app.unmount() }
})

test('components preserve sandbox and pure text rendering', async () => {
  const artifacts = await readFile(resolve(root, 'src/components/ArtifactPanel.vue'), 'utf8')
  const message = await readFile(resolve(root, 'src/components/MessageItem.vue'), 'utf8')
  assert.equal((artifacts.match(/sandbox="allow-scripts"/g) || []).length, 2)
  assert.match(artifacts, /showModal\(\)/)
  assert.match(artifacts, /value\[0\]\?\.path/)
  assert.match(artifacts, /closeReport\(\); selectedReport\.value = ''/)
  assert.doesNotMatch(artifacts, /allow-same-origin/)
  assert.doesNotMatch(message, /v-html/)
})
