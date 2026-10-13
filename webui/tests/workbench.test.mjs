import assert from 'node:assert/strict'
import { test, after } from 'node:test'
import { mkdtemp, readFile, writeFile, mkdir, rm } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'
import { createRenderer, nextTick, reactive, h } from 'vue'
import { parse, compileScript } from '@vue/compiler-sfc'

// Compile the actual TS modules to a disposable directory, no testing dependency needed.
const root = resolve(import.meta.dirname, '..')
await mkdir(resolve(root, 'node_modules/.tmp'), { recursive: true })
const out = await mkdtemp(resolve(root, 'node_modules/.tmp/workbench-test-'))
for (const file of ['projectTypes.ts', 'projectApi.ts', 'composables/useProject.ts', 'types.ts', 'api.ts', 'composables/eventReducer.ts', 'composables/useWorkbench.ts', 'templates/attical.ts']) {
  const source = await readFile(resolve(root, 'src', file), 'utf8')
  let code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
  code = code.replace(/from '(\.[^']+)'/g, "from '$1.js'")
  const destination = resolve(out, file.replace(/\.ts$/, '.js'))
  await mkdir(dirname(destination), { recursive: true })
  await writeFile(destination, code)
}
// 编译真实组件，用 Vue 内存渲染器检查视图切换，无浏览器依赖。
for (const file of ['App.vue', ...['ProjectPanel', 'TaskSidebar', 'ConversationPanel', 'MessageItem', 'TaskComposer', 'ArtifactPanel', 'ProgressPanel'].map(name => `components/${name}.vue`)]) {
  const source = await readFile(resolve(root, 'src', file), 'utf8')
  const { descriptor } = parse(source)
  const script = compileScript(descriptor, { id: file, inlineTemplate: true })
  let code = ts.transpileModule(script.content, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
  code = code.replace(/from (['"])(\.[^'"]+)\1/g, (_, quote, path) => `from ${quote}${path.replace(/\.vue$/, '')}.js${quote}`)
  const destination = resolve(out, file.replace(/\.vue$/, '.js'))
  await mkdir(dirname(destination), { recursive: true })
  await writeFile(destination, code)
}
const { default: ProgressPanel } = await import(pathToFileURL(resolve(out, 'components/ProgressPanel.js')))
const { default: App } = await import(pathToFileURL(resolve(out, 'App.js')))
const { applyTaskEvent, initialConversation } = await import(pathToFileURL(resolve(out, 'composables/eventReducer.js')))
const api = await import(pathToFileURL(resolve(out, 'api.js')))
const { useWorkbench } = await import(pathToFileURL(resolve(out, 'composables/useWorkbench.js')))
const { default: TaskSidebar } = await import(pathToFileURL(resolve(out, 'components/TaskSidebar.js')))
const originalWindow = globalThis.window
const originalFetch = globalThis.fetch
const rpc = data => ({ type: 'agent', data })
const assistant = (text, thinking = '') => ({ role: 'assistant', content: [{ type: 'text', text }, { type: 'thinking', thinking }] })
const response = data => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } })
const waitFor = async predicate => {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await new Promise(r => setTimeout(r, 5)) }
  assert.fail('等待状态超时')
}
after(async () => { globalThis.fetch = originalFetch; globalThis.window = originalWindow; await rm(out, { recursive: true, force: true }) })

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

const elements = []
const renderer = createRenderer({
  createElement: tag => {
    const el = { tag, tagName: tag.toUpperCase(), style: {}, props: {}, text: '', children: [],
      options: [], getRootNode() { return {} }, close() {}, showModal() {}, addEventListener() {}, removeEventListener() {} }
    elements.push(el)
    return el
  },
  createText: text => ({ text }), createComment: text => ({ text }),
  insert(el, parent, anchor = null) {
    if (el.parent) el.parent.children.splice(el.parent.children.indexOf(el), 1)
    parent.children ||= []
    const index = anchor ? parent.children.indexOf(anchor) : -1
    parent.children.splice(index < 0 ? parent.children.length : index, 0, el)
    el.parent = parent
  },
  remove(el) { if (el.parent) el.parent.children.splice(el.parent.children.indexOf(el), 1); el.parent = null },
  setText(el, text) { el.text = text },
  setElementText(el, text) { el.text = text; el.children = [] },
  parentNode: el => el.parent,
  nextSibling: el => el.parent?.children[el.parent.children.indexOf(el) + 1] || null,
  patchProp(el, key, prev, next) { el.props[key] = next },
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

test('视图切换保留对话实例与实时订阅，切任务返回对话', async () => {
  elements.length = 0
  const streams = new Map()
  let eventReads = 0
  let detailReads = 0
  const task = id => ({ task_id: id, prompt: `prompt-${id}`, status: 'running', created_at: '' })
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_tasks') return response({ tasks: [task('A'), task('B')] })
    const id = new URL(url, 'http://local').searchParams.get('task_id')
    if (url.startsWith('/task/get_task')) {
      detailReads++
      return response({ task: task(id), files: [{ path: 'report.html', kind: 'report_html', size: 10 }] })
    }
    eventReads++
    return new Response(new ReadableStream({ start(c) { streams.set(id, { c, signal: options.signal }) } }))
  }
  const app = renderer.createApp(App)
  app.mount({})
  const control = label => elements.find(el => el.tag === 'button' && el.text === label && el.props['aria-controls'] === 'main-view')
  const click = async label => { control(label).props.onClick(); await nextTick() }
  try {
    await waitFor(() => streams.has('A'))
    const conversation = elements.find(el => el.props['aria-label'] === '任务会话')
    for (const view of ['进度预览', '验证结果报告', '文件下载', '对话']) {
      await click(view)
      assert.equal(eventReads, 1)
      assert.equal(detailReads, 1)
      assert.equal(streams.get('A').signal.aborted, false)
      assert.equal(conversation.style.display, view === '对话' ? undefined : 'none')
    }
    assert.equal(elements.filter(el => el.props['aria-label'] === '任务会话').length, 1)
    const scroll = elements.find(el => el.props.class === 'message-scroll')
    Object.assign(scroll, { scrollTop: 120, scrollHeight: 1000, clientHeight: 300 })
    scroll.props.onScrollPassive()
    await click('进度预览')
    const send = data => streams.get('A').c.enqueue(new TextEncoder().encode(JSON.stringify(rpc(data)) + '\n'))
    send({ type: 'tool_execution_start', toolCallId: 'live-tool', toolName: 'bash' })
    await waitFor(() => elements.some(el => el.text === 'live-tool'))
    send({ type: 'tool_execution_end', toolCallId: 'live-tool', isError: true, result: 'failed' })
    await waitFor(() => elements.some(el => el.tag === 'span' && el.text === '失败'))
    await click('对话')
    assert.equal(eventReads, 1)
    assert.equal(conversation.style.display, undefined)
    assert.equal(scroll.scrollTop, 120)
    await click('文件下载')
    // 任务卡的 ID 在子节点内，选择未选中的卡片。
    const taskB = elements.find(el => el.tag === 'button' && el.props.class?.includes('task-select') && el.props['aria-current'] !== 'true')
    taskB.props.onClick()
    await waitFor(() => streams.has('B'))
    await nextTick()
    assert.equal(control('对话').props['aria-pressed'], true)
    assert.equal(conversation.style.display, undefined)
    assert.equal(streams.get('A').signal.aborted, true)
    assert.equal(eventReads, 2)
  } finally {
    app.unmount()
    for (const { c } of streams.values()) c.close()
  }
})

test('布局约束：精简顶栏与任务卡、右侧表单和按钮、中间产物', async () => {
  const source = async path => readFile(resolve(root, 'src', path), 'utf8')
  const app = await source('App.vue')
  const sidebar = await source('components/TaskSidebar.vue')
  const composer = await source('components/TaskComposer.vue')
  const progress = await source('components/ProgressPanel.vue')
  const css = await source('style.css')
  assert.match(app, /<header class="app-header">[\s\S]*<h1>软件IP验证<\/h1>[\s\S]*aria-label="验证模式"/)
  assert.doesNotMatch(app, /brand-mark|WORKSPACE|Agent 验证工作台/)
  assert.doesNotMatch(sidebar, /item\.prompt|created_at|<time|无提示词|TASKS|sidebar-foot/)
  assert.match(sidebar, /item\.task_id/)
  assert.match(sidebar, /statusLabel\(item.status\)/)
  const center = app.slice(app.indexOf('id="main-view"'), app.indexOf('<aside class="panel task-controls"'))
  const right = app.slice(app.indexOf('<aside class="panel task-controls"'))
  assert.match(center, /<ArtifactPanel/)
  assert.match(center, /v-show="activeView === 'conversation'"/)
  assert.doesNotMatch(center, /<TaskComposer/)
  assert.match(right, /<TaskComposer[\s\S]*<nav class="view-controls"/)
  assert.doesNotMatch(right, /<ArtifactPanel/)
  assert.match(app, /@click="activeView = view.id"/)
  assert.match(app, /watch\(selectedId,[\s\S]*activeView.value = 'conversation'/)
  assert.match(composer, /prompt = atticalPrompt/)
  assert.match(css, /grid-template-columns:220px minmax\(0,1fr\) 340px/)
  assert.match(css, /\.task-select strong \{[^}]*min-width:0;[^}]*overflow-wrap:anywhere/)
  assert.doesNotMatch(css, /\.brand|\.eyebrow|\.tabs|\.sidebar-foot|box-shadow|linear-gradient/)
  assert.match(progress, /props.messages.filter\(message => message.kind === 'tool'\)/)
  assert.doesNotMatch(progress, /百分比|\bcase\b|百分之|验证成功|<progress/)
})


test('进度根据真实工具状态响应更新，不把工具成功当作任务完成', async () => {
  elements.length = 0
  const props = reactive({
    task: { task_id: 'A', prompt: '', status: 'running', created_at: '' }, selectedId: 'A',
    streamState: 'live', loading: false, error: '',
    messages: [
      { id: 'u', kind: 'user', text: 'prompt' },
      { id: 'a', kind: 'tool', text: '', toolName: 'bash', state: 'running' },
      { id: 'b', kind: 'tool', text: '', toolName: 'read', state: 'success' },
      { id: 'c', kind: 'tool', text: '', toolName: 'bash', state: 'error' },
      { id: 'd', kind: 'assistant', text: 'output' },
    ],
  })
  const app = renderer.createApp(ProgressPanel, props)
  app.mount({})
  const values = () => elements.filter(el => el.tag === 'dd').map(el => el.text)
  try {
    assert.deepEqual(values(), ['A', '运行中', '接收事件中', '3', '1', '1', '1'])
    props.messages[1].state = 'success'
    await nextTick()
    assert.deepEqual(values(), ['A', '运行中', '接收事件中', '3', '0', '2', '1'])
  } finally { app.unmount() }
})

const deferred = () => {
  let resolve
  const promise = new Promise(r => { resolve = r })
  return { promise, resolve }
}
// 所有删除请求由 fetch mock 接管，不访问真实任务或启动 Agent。
function deletionFixture(ids = ['A', 'B']) {
  const streams = []
  const requests = []
  const deletion = deferred()
  let listHandler
  const task = id => ({ task_id: id, prompt: `prompt-${id}`, status: 'running', created_at: '' })
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options = {}) => {
    requests.push({ url, options })
    if (url === '/task/list_tasks') return listHandler ? listHandler() : response({ tasks: ids.map(task) })
    const id = new URL(url, 'http://local').searchParams.get('task_id')
    if (url.startsWith('/task/delete_task')) return deletion.promise
    if (url.startsWith('/task/get_task')) return response({ task: task(id), files: [{ path: 'report.html', kind: 'report_html', size: 10 }] })
    return new Response(new ReadableStream({ start(c) { streams.push({ id, c, signal: options.signal }) } }))
  }
  const { app, w } = mountedWorkbench()
  return { app, w, streams, requests, deletion, task,
    setList: handler => { listHandler = handler },
    async initialize() { await w.initialize(); await waitFor(() => streams.length === 1) },
    close() { app.unmount(); for (const s of streams) { try { s.c.close() } catch {} } },
  }
}

test('DELETE 编码任务 ID，复用 checked 显示 404/409', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/task/delete_task?task_id=a%20%2F%23%E4%B8%AD')
    assert.equal(options.method, 'DELETE')
    return response({ task_id: 'a /#中', status: 'deleted' })
  }
  await api.deleteTask('a /#中')
  for (const status of [404, 409]) {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: `删除错误 ${status}` }), { status })
    await assert.rejects(api.deleteTask('A'), new RegExp(`删除错误 ${status}`))
  }
})

test('取消永久删除确认不请求、不切任务、不打断订阅', async () => {
  const f = deletionFixture()
  try {
    await f.initialize()
    const count = f.requests.length
    globalThis.window.confirm = text => {
      assert.match(text, /永久删除任务.*A/)
      assert.match(text, /全部文件不可恢复，运行任务将先停止/)
      return false
    }
    await f.w.removeTask('A')
    assert.equal(f.requests.length, count)
    assert.equal(f.w.selectedId.value, 'A')
    assert.equal(f.streams[0].signal.aborted, false)
    assert.equal(f.w.deletingId.value, '')
  } finally { f.close() }
})

test('删当前任务阻止重复点击、断订阅、清视图并选择剩余任务；旧列表和事件不能复活', async () => {
  const f = deletionFixture()
  try {
    await f.initialize()
    const oldList = deferred()
    f.setList(() => oldList.promise)
    const refreshing = f.w.refreshTasks()
    const deleting = f.w.removeTask('A')
    assert.equal(f.streams[0].signal.aborted, true)
    assert.equal(f.w.deletingId.value, 'A')
    await f.w.removeTask('A')
    await f.w.removeTask('B')
    assert.equal(f.requests.filter(r => r.options.method === 'DELETE').length, 1)
    const freshList = deferred()
    f.setList(() => freshList.promise)
    f.deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await waitFor(() => f.streams.length === 2)
    assert.equal(f.w.selectedId.value, 'B')
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['B'])
    assert.equal(f.w.task.value.task_id, 'B')
    assert.deepEqual(f.w.messages.value.map(m => m.text), ['prompt-B'])
    assert.equal(f.w.detailError.value, '')
    assert.equal(f.w.streamError.value, '')
    f.streams[0].c.enqueue(new TextEncoder().encode(JSON.stringify(rpc({ type: 'message_start', message: assistant('旧输出') })) + '\n'))
    oldList.resolve(response({ tasks: [f.task('A')] }))
    await refreshing
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['B'])
    freshList.resolve(response({ tasks: [f.task('A'), f.task('B')] }))
    await deleting
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['B'])
    assert.deepEqual(f.w.messages.value.map(m => m.text), ['prompt-B'])
    assert.equal(f.streams[1].signal.aborted, false)
  } finally { f.close() }
})

test('删除唯一当前任务清空 task/messages/files/loading/stream/error', async () => {
  const f = deletionFixture(['A'])
  try {
    await f.initialize()
    f.w.detailError.value = '旧详情错误'
    f.w.streamError.value = '旧流错误'
    const deleting = f.w.removeTask('A')
    f.deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await deleting
    assert.equal(f.w.selectedId.value, '')
    assert.equal(f.w.task.value, null)
    assert.deepEqual(f.w.messages.value, [])
    assert.deepEqual(f.w.files.value, [])
    assert.equal(f.w.streamState.value, 'idle')
    assert.equal(f.w.detailLoading.value, false)
    assert.equal(f.w.detailError.value, '')
    assert.equal(f.w.streamError.value, '')
    assert.deepEqual(f.w.tasks.value, [])
  } finally { f.close() }
})

test('删非当前任务不打断当前订阅和视图', async () => {
  const f = deletionFixture()
  try {
    await f.initialize()
    const task = f.w.task.value
    const files = f.w.files.value
    const deleting = f.w.removeTask('B')
    assert.equal(f.streams[0].signal.aborted, false)
    f.deletion.resolve(response({ task_id: 'B', status: 'deleted' }))
    await deleting
    assert.equal(f.w.selectedId.value, 'A')
    assert.equal(f.w.task.value, task)
    assert.equal(f.w.files.value, files)
    assert.equal(f.streams.length, 1)
    assert.equal(f.streams[0].signal.aborted, false)
  } finally { f.close() }
})

for (const outcome of ['success', '404', '409', 'network']) {
  test(`删除中切到 B，${outcome} 不抢焦点或打断 B，失败不假删`, async () => {
    const f = deletionFixture()
    try {
      await f.initialize()
      const deleting = f.w.removeTask('A')
      void f.w.selectTask('B')
      await waitFor(() => f.streams.length === 2)
      if (outcome === 'success') f.deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
      else if (outcome === 'network') f.deletion.resolve(Promise.reject(new Error('网络中断')))
      else f.deletion.resolve(new Response(JSON.stringify({ detail: `删除失败 ${outcome}` }), { status: Number(outcome) }))
      await deleting
      assert.equal(f.w.selectedId.value, 'B')
      assert.equal(f.w.task.value.task_id, 'B')
      assert.equal(f.streams[1].signal.aborted, false)
      assert.equal(f.streams.length, 2)
      assert.equal(f.w.tasks.value.some(t => t.task_id === 'A'), outcome !== 'success')
      if (outcome !== 'success') {
        assert.match(f.w.deleteError.value, /永久删除任务「A」失败/)
        await f.w.refreshTasks()
        assert.match(f.w.deleteError.value, /失败/)
      }
    } finally { f.close() }
  })
}

test('404 失败保留任务卡；列表刷新不移除 pending 卡，恢复仍选中任务订阅', async () => {
  const f = deletionFixture()
  try {
    await f.initialize()
    const deleting = f.w.removeTask('A')
    f.setList(() => response({ tasks: [f.task('B')] }))
    await f.w.refreshTasks()
    assert.equal(f.w.tasks.value.some(t => t.task_id === 'A'), true)
    f.deletion.resolve(new Response(JSON.stringify({ detail: '任务不存在' }), { status: 404 }))
    await deleting
    await waitFor(() => f.streams.length === 2)
    assert.equal(f.w.tasks.value.some(t => t.task_id === 'A'), true)
    assert.match(f.w.deleteError.value, /任务不存在/)
    assert.equal(f.w.selectedId.value, 'A')
    assert.equal(f.streams[1].signal.aborted, false)
    assert.equal(f.w.deletingId.value, '')
  } finally { f.close() }
})

test('TaskSidebar 选择与删除是独立 button，无嵌套，pending 和错误可见', async () => {
  const props = reactive({ tasks: [{ task_id: 'A', status: 'running' }], selectedId: 'A', loading: false,
    error: '', deletingId: '', deleteError: '', onSelect: id => selected.push(id), onDelete: id => removed.push(id) })
  const selected = [], removed = []
  const rootElement = {}
  // 用实际 sidebar 组件和内存渲染器验证 DOM 结构与事件接线。
  const sidebarApp = renderer.createApp({ render: () => h(TaskSidebar, props) })
  sidebarApp.mount(rootElement)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  try {
    const buttons = nodes().filter(el => el.tag === 'button')
    for (const button of buttons) assert.equal(descendants(button).slice(1).some(el => el.tag === 'button'), false)
    const remove = buttons.find(el => el.props.class === 'task-delete')
    remove.props.onClick()
    assert.deepEqual(removed, ['A'])
    assert.deepEqual(selected, [])
    props.deletingId = 'A'
    props.deleteError = '永久删除失败：409'
    await nextTick()
    assert.equal(remove.props.disabled, true)
    assert.equal(remove.text, '删除中…')
    assert.ok(nodes().some(el => el.props?.role === 'alert' && el.text === props.deleteError))
  } finally { sidebarApp.unmount() }
})

test('删除时迟到的详情响应不恢复任务或启动事件订阅', async () => {
  const detail = deferred()
  const deletion = deferred()
  let signal, eventReads = 0
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_tasks') return response({ tasks: [] })
    if (options.method === 'DELETE') return deletion.promise
    if (url.startsWith('/task/get_task')) { signal = options.signal; return detail.promise }
    eventReads++
    return new Response('')
  }
  const { app, w } = mountedWorkbench()
  try {
    const selecting = w.selectTask('A')
    const deleting = w.removeTask('A')
    assert.equal(signal.aborted, true)
    deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await deleting
    detail.resolve(response({ task: { task_id: 'A', prompt: '旧详情', status: 'running' }, files: [{ path: 'old.html' }] }))
    await selecting
    assert.equal(w.selectedId.value, '')
    assert.equal(w.task.value, null)
    assert.deepEqual(w.files.value, [])
    assert.deepEqual(w.messages.value, [])
    assert.equal(eventReads, 0)
  } finally { app.unmount() }
})

test('删除中迟到的 reconcile 详情不串回删除任务', async () => {
  const detail = deferred(), deletion = deferred()
  let reads = 0
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_tasks') return response({ tasks: [] })
    if (options.method === 'DELETE') return deletion.promise
    if (url.startsWith('/task/get_task')) {
      if (++reads === 2) return detail.promise
      return response({ task: { task_id: 'A', prompt: 'A', status: 'running' }, files: [] })
    }
    return new Response('')
  }
  const { app, w } = mountedWorkbench()
  try {
    const selecting = w.selectTask('A')
    await waitFor(() => reads === 2)
    const deleting = w.removeTask('A')
    deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await deleting
    detail.resolve(response({ task: { task_id: 'A', prompt: '旧结果', status: 'completed' }, files: [{ path: 'old.html' }] }))
    await selecting
    assert.equal(w.task.value, null)
    assert.equal(w.selectedId.value, '')
    assert.deepEqual(w.files.value, [])
  } finally { app.unmount() }
})

test('App 删除接线清除报告 iframe 和展开 dialog，不清空用户输入', async () => {
  const originalDocument = globalThis.Document, originalShadowRoot = globalThis.ShadowRoot
  globalThis.Document = class {}
  globalThis.ShadowRoot = class {}
  const streams = [], deletion = deferred()
  const task = { task_id: 'A', prompt: 'A', status: 'running' }
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_tasks') return response({ tasks: [task] })
    if (options.method === 'DELETE') return deletion.promise
    if (url.startsWith('/task/get_task')) return response({ task, files: [{ path: 'report.html', kind: 'report_html', size: 10 }] })
    return new Response(new ReadableStream({ start(c) { streams.push({ c, signal: options.signal }) } }))
  }
  const rootElement = {}
  const app = renderer.createApp(App)
  app.mount(rootElement)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  try {
    await waitFor(() => streams.length === 1)
    nodes().find(el => el.props?.['aria-controls'] === 'main-view' && el.text === '验证结果报告').props.onClick()
    await nextTick()
    nodes().find(el => el.tag === 'button' && el.props?.['aria-haspopup'] === 'dialog').props.onClick()
    await nextTick()
    assert.ok(nodes().some(el => el.tag === 'dialog'))
    assert.ok(nodes().some(el => el.tag === 'iframe'))
    const input = nodes().find(el => el.tag === 'textarea')
    input.props['onUpdate:modelValue']?.('用户保留的输入')
    await nextTick()
    const inputValue = input.value
    assert.equal(inputValue, '用户保留的输入')
    nodes().find(el => el.props?.class === 'task-delete').props.onClick()
    deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await waitFor(() => !nodes().some(el => el.tag === 'iframe' || el.tag === 'dialog'))
    assert.equal(streams[0].signal.aborted, true)
    assert.equal(input.value, inputValue)
    assert.equal(nodes().some(el => el.props?.class === 'task-card'), false)
  } finally {
    app.unmount()
    for (const stream of streams) stream.c.close()
    globalThis.Document = originalDocument
    globalThis.ShadowRoot = originalShadowRoot
  }
})

test('永久删除后可重新创建相同 ID，新任务不被已删除 ID 过滤', async () => {
  const f = deletionFixture(['A'])
  try {
    await f.initialize()
    const deleting = f.w.removeTask('A')
    f.deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await deleting
    const mockFetch = globalThis.fetch
    globalThis.fetch = async (url, options) => url === '/task/create_task'
      ? response({ task_id: 'A', status: 'created' }) : mockFetch(url, options)
    assert.equal(await f.w.submit('A', '新提示词'), true)
    await waitFor(() => f.streams.length === 2)
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['A'])
    assert.equal(f.w.selectedId.value, 'A')
    assert.equal(f.streams[1].signal.aborted, false)
  } finally { f.close() }
})


test('删除完成后新列表确认 ID 缺失，再之后 fresh list 同 ID 新任务可见', async () => {
  const f = deletionFixture(['A'])
  try {
    await f.initialize()
    const deleting = f.w.removeTask('A')
    f.deletion.resolve(response({ task_id: 'A', status: 'deleted' }))
    await deleting
    // 最新列表仍含已删除 ID 时继续过滤，不释放标记。
    await f.w.refreshTasks()
    assert.deepEqual(f.w.tasks.value, [])
    const oldList = deferred()
    f.setList(() => oldList.promise)
    const refreshing = f.w.refreshTasks()
    f.setList(() => response({ tasks: [] }))
    await f.w.refreshTasks()
    // 已确认缺失后，旧 revision 仍不能复活任务。
    oldList.resolve(response({ tasks: [f.task('A')] }))
    await refreshing
    assert.deepEqual(f.w.tasks.value, [])
    const recreated = { ...f.task('A'), prompt: '其他页面重建的新任务', status: 'created' }
    f.setList(() => response({ tasks: [recreated] }))
    await f.w.refreshTasks()
    assert.deepEqual(f.w.tasks.value, [recreated])
    assert.equal(f.w.selectedId.value, '')
    assert.equal(f.requests.some(r => r.url === '/task/create_task'), false)
  } finally { f.close() }
})

const { useProject } = await import(pathToFileURL(resolve(out, 'composables/useProject.js')))
const projectApi = await import(pathToFileURL(resolve(out, 'projectApi.js')))
const { ref } = await import('vue')
const flushProject = async () => { for (let i = 0; i < 40; i++) await Promise.resolve(); await nextTick() }
function mountedProject() {
  let project
  const active = ref(true)
  const app = renderer.createApp({ setup() { project = useProject(active); return () => null } })
  app.mount({})
  return { app, p: project, active }
}
function projectClock() {
  const originalSet = globalThis.setTimeout, originalClear = globalThis.clearTimeout
  const timers = new Map()
  let serial = 0
  globalThis.setTimeout = (callback, delay) => { assert.equal(delay, 2000); timers.set(++serial, callback); return serial }
  globalThis.clearTimeout = id => timers.delete(id)
  return { timers, tick() { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach(fn => fn()) },
    restore() { globalThis.setTimeout = originalSet; globalThis.clearTimeout = originalClear } }
}
const projectProgress = (id, status = 'running') => ({ projectID: id, status, total: 1, finished: status === 'running' ? 0 : 1, tasks: [{ task_id: `${id}-task`, status }] })
const projectResults = id => ({ projectID: id, tasks: [{ task_id: `${id}-task`, status: 'completed', files: [{ path: '报告 #.html', size: 12, kind: 'report_html', download_url: '/task/get_file?task_id=t&path=report.html&download=true' }] }] })

test('项目 API 编码、默认提示词、409 和 404 错误', async () => {
  const calls = []
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response({ projectID: '中 &/#', status: 'accepted' }) }
  const signal = new AbortController().signal
  await projectApi.createProject('中 &/#', '', signal)
  assert.deepEqual(JSON.parse(calls[0].options.body), { projectID: '中 &/#' })
  await projectApi.createProject('中 &/#', '自定义 CBMC', signal)
  assert.equal(JSON.parse(calls[1].options.body).prompt, '自定义 CBMC')
  await projectApi.getProjectProgress('中 &/#', signal)
  await projectApi.getProjectResults('中 &/#', signal)
  assert.equal(calls[2].url, '/project/get_progress?projectID=%E4%B8%AD%20%26%2F%23')
  assert.equal(calls[3].url, '/project/get_results?projectID=%E4%B8%AD%20%26%2F%23')
  assert.ok(calls.every(call => call.options.signal === signal))
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: '项目已存在' }), { status: 409 })
  await assert.rejects(projectApi.createProject('p', '', signal), /项目已存在/)
  globalThis.fetch = async () => new Response('Not Found', { status: 404 })
  await assert.rejects(projectApi.getProjectProgress('p', signal), /HTTP 404/)
})

test('项目提交后串行查询，每 2 秒轮询，所有终态停止', async () => {
  const clock = projectClock()
  const { app, p } = mountedProject()
  const calls = []
  let status = 'running'
  let inFlight = 0, maximum = 0
  globalThis.fetch = async (url, options) => {
    maximum = Math.max(maximum, ++inFlight)
    calls.push(url)
    await Promise.resolve()
    inFlight--
    if (url.endsWith('create_project')) {
      assert.deepEqual(JSON.parse(options.body), { projectID: 'demo', prompt: '提示' })
      return response({ projectID: 'demo', status: 'accepted' })
    }
    return response(url.includes('get_progress') ? projectProgress('demo', status) : projectResults('demo'))
  }
  try {
    p.projectID.value = 'demo'; p.prompt.value = '提示'; p.submit()
    await flushProject()
    assert.deepEqual(calls, ['/project/create_project', '/project/get_progress?projectID=demo', '/project/get_results?projectID=demo'])
    assert.equal(p.results.value.tasks[0].files[0].size, 12)
    assert.equal(clock.timers.size, 1)
    clock.tick(); await flushProject()
    assert.equal(calls.length, 5)
    assert.equal(maximum, 1)
    for (const terminal of ['completed', 'failed', 'cancelled', 'empty']) {
      status = terminal
      p.query(); await flushProject()
      assert.equal(p.progress.value.status, terminal)
      assert.equal(p.polling.value, false)
      assert.equal(clock.timers.size, 0)
      const count = calls.length
      clock.tick(); await flushProject()
      assert.equal(calls.length, count)
    }
  } finally { app.unmount(); clock.restore() }
})

test('换 ID 隔离迟到进度与结果，请求不重叠，卸载取消请求', async () => {
  const clock = projectClock()
  const { app, p } = mountedProject()
  const oldProgress = deferred(), oldResults = deferred()
  const calls = [], signals = []
  globalThis.fetch = (url, options) => {
    calls.push(url); signals.push(options.signal)
    if (url.endsWith('projectID=A')) return oldProgress.promise
    if (url.includes('get_results') && url.endsWith('projectID=B')) return oldResults.promise
    const id = new URL(url, 'http://local').searchParams.get('projectID')
    return Promise.resolve(response(url.includes('get_progress') ? projectProgress(id, 'completed') : projectResults(id)))
  }
  try {
    p.projectID.value = 'A'; p.query()
    p.projectID.value = 'B'; p.query()
    assert.equal(signals[0].aborted, true)
    assert.equal(calls.length, 1)
    oldProgress.resolve(response(projectProgress('A')))
    await flushProject()
    assert.equal(p.progress.value.projectID, 'B')
    assert.equal(calls.length, 3)
    p.projectID.value = 'C'; p.query()
    assert.equal(p.progress.value, null)
    assert.equal(signals[2].aborted, true)
    oldResults.resolve(response(projectResults('B')))
    await flushProject()
    assert.equal(p.progress.value.projectID, 'C')
    assert.equal(p.results.value.projectID, 'C')
    assert.equal(clock.timers.size, 0)
    p.projectID.value = 'A'; p.query()
    app.unmount()
    assert.equal(signals.at(-1).aborted, true)
    await flushProject()
    assert.equal(clock.timers.size, 0)
  } finally { app.unmount(); clock.restore() }
})

test('隐藏时取消迟到响应，恢复续查；切换 ID 与卸载清理计时器', async () => {
  const clock = projectClock()
  const { app, p, active } = mountedProject()
  const late = deferred()
  let reads = 0
  let signal
  globalThis.fetch = async (url, options) => {
    if (++reads === 1) { signal = options.signal; return late.promise }
    return response(url.includes('get_progress') ? projectProgress('demo') : projectResults('demo'))
  }
  try {
    p.projectID.value = 'demo'; p.query()
    active.value = false
    assert.equal(signal.aborted, true)
    late.resolve(response(projectProgress('demo', 'failed')))
    await flushProject()
    assert.equal(p.progress.value, null)
    assert.equal(reads, 1)
    active.value = true; await flushProject()
    assert.equal(p.progress.value.status, 'running')
    assert.equal(clock.timers.size, 1)
    active.value = false
    assert.equal(clock.timers.size, 0)
    active.value = true; await flushProject()
    assert.equal(clock.timers.size, 1)
    p.projectID.value = 'other'
    assert.equal(clock.timers.size, 0)
    assert.equal(p.polling.value, false)
    p.query(); await flushProject()
    app.unmount()
    assert.equal(clock.timers.size, 0)
  } finally { app.unmount(); clock.restore() }
})

test('查询和提交错误停止轮询，可手动查询恢复', async () => {
  const clock = projectClock()
  const { app, p } = mountedProject()
  let failure = 'create'
  globalThis.fetch = async url => {
    if (failure === 'create') return new Response(JSON.stringify({ detail: '项目已存在' }), { status: 409 })
    if (url.includes('get_results') && failure === 'results') throw new Error('结果暂不可用')
    if (failure === 'progress') return new Response(JSON.stringify({ detail: '未找到项目' }), { status: 404 })
    return response(url.includes('get_progress') ? projectProgress('demo') : projectResults('demo'))
  }
  try {
    p.submit(); assert.equal(p.error.value, '请输入项目 ID')
    p.projectID.value = 'demo'; p.submit(); await flushProject()
    assert.equal(p.error.value, '项目已存在')
    for (const phase of ['progress', 'results']) {
      failure = phase; p.query(); await flushProject()
      assert.match(p.error.value, /未找到项目|结果暂不可用/)
      assert.equal(p.polling.value, false)
      assert.equal(clock.timers.size, 0)
    }
    failure = ''; p.query(); await flushProject()
    assert.equal(p.error.value, '')
    assert.equal(clock.timers.size, 1)
  } finally { app.unmount(); clock.restore() }
})

test('项目页切换保留单 IP 输入和订阅，显示下载并可查看任务', async () => {
  const originalDocument = globalThis.Document, originalShadowRoot = globalThis.ShadowRoot
  globalThis.Document = class {}
  globalThis.ShadowRoot = class {}
  const streams = [], details = []
  let listReads = 0
  const task = id => ({ task_id: id, prompt: id, status: 'running' })
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_tasks') { listReads++; return response({ tasks: [task('A'), task('demo-task')] }) }
    if (url.startsWith('/project/')) return response(url.includes('get_progress') ? projectProgress('demo', 'completed') : projectResults('demo'))
    const id = new URL(url, 'http://local').searchParams.get('task_id')
    if (url.startsWith('/task/get_task')) { details.push(id); return response({ task: task(id), files: [] }) }
    return new Response(new ReadableStream({ start(c) { streams.push({ id, c, signal: options.signal }) } }))
  }
  const rootElement = {}
  const app = renderer.createApp(App)
  app.mount(rootElement)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  const button = label => nodes().find(el => el.tag === 'button' && el.text === label)
  try {
    await waitFor(() => streams.length === 1)
    const textarea = nodes().find(el => el.tag === 'textarea' && el.props.placeholder === '描述验证目标与约束…')
    const taskInput = nodes().find(el => el.tag === 'input' && el.props.placeholder === '例如 attical-check-01')
    textarea.props['onUpdate:modelValue']('保留单 IP 提示词')
    taskInput.props['onUpdate:modelValue']('my-task')
    await nextTick()
    const workspace = nodes().find(el => el.props?.class === 'workspace')
    const projectPanel = nodes().find(el => el.props?.class === 'project-panel')
    button('项目验证').props.onClick(); await nextTick()
    assert.equal(workspace.style.display, 'none')
    assert.equal(projectPanel.style.display, undefined)
    assert.equal(streams[0].signal.aborted, false)
    nodes().find(el => el.props?.id === 'project-id').props['onUpdate:modelValue']('demo')
    nodes().find(el => el.props?.id === 'project-prompt').props['onUpdate:modelValue']('项目提示词')
    await nextTick()
    button('查询已有项目').props.onClick()
    await waitFor(() => nodes().some(el => el.tag === 'a' && el.props.href?.includes('/task/get_file')))
    const download = nodes().find(el => el.tag === 'a' && el.props.href?.includes('/task/get_file'))
    assert.equal(download.text, '报告 #.html')
    assert.equal(download.props.href, projectResults('demo').tasks[0].files[0].download_url)
    button('单 IP 验证').props.onClick(); await nextTick()
    assert.equal(workspace.style.display, undefined)
    assert.equal(streams[0].signal.aborted, false)
    assert.equal(streams.length, 1)
    assert.equal(textarea.value, '保留单 IP 提示词')
    assert.equal(taskInput.value, 'my-task')
    button('项目验证').props.onClick(); await nextTick()
    assert.equal(nodes().find(el => el.props?.id === 'project-prompt').value, '项目提示词')
    const previousLists = listReads
    button('查看任务').props.onClick()
    await waitFor(() => streams.length === 2)
    await nextTick()
    assert.equal(workspace.style.display, undefined)
    assert.equal(details.at(-1), 'demo-task')
    assert.ok(listReads > previousLists)
    assert.equal(streams[0].signal.aborted, true)
    assert.equal(textarea.value, '保留单 IP 提示词')
  } finally {
    app.unmount()
    streams.forEach(stream => stream.c.close())
    globalThis.Document = originalDocument; globalThis.ShadowRoot = originalShadowRoot
  }
})
