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
for (const file of ['App.vue', ...['ProjectPanel', 'TaskSidebar', 'ConversationPanel', 'MessageItem', 'ArtifactPanel', 'ProgressPanel'].map(name => `components/${name}.vue`)]) {
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

test('真实 RPC 首消息仅出现一次，快照替换增量，思考保持纯文本', () => {
  const state = initialConversation()
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

test('API 编码、自动任务 ID 与 userprompt 契约', async () => {
  assert.equal(api.fileUrl('a b', 'reports/a #中.html', true), '/task/get_file?task_id=a%20b&path=reports%2Fa%20%23%E4%B8%AD.html&download=true')
  assert.equal(api.taskZipUrl('a b'), '/task/download_task?task_id=a%20b')
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
    assert.equal(url, '/task/create_task')
    assert.deepEqual(JSON.parse(options.body), { ip_name: 'AttiCal', tool: 'CBMC', userprompt: '' })
    return response({ task_id: 'auto1234' })
  }
  assert.deepEqual(await api.createTask('AttiCal', 'CBMC', ''), { task_id: 'auto1234' })
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: '任务已存在' }), { status: 409 })
  await assert.rejects(api.createTask('AttiCal', 'CBMC', ''), /任务已存在/)
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

test('切换任务取消旧订阅、不串话，metadata 不注入首消息', async () => {
  const streams = new Map()
  const detail = id => ({ task: { task_id: id, prompt: `prompt-${id}`, status: 'running', created_at: '' }, files: [{ path: `${id}/report.html`, kind: 'report_html', size: 20 }] })
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
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
    assert.deepEqual(w.messages.value, [])
    const selectingB = w.selectTask('B')
    await waitFor(() => streams.has('B'))
    assert.equal(streams.get('A').signal.aborted, true)
    // Simulate a late old event even when a transport doesn't immediately abort read().
    const send = (id, text) => streams.get(id).c.enqueue(new TextEncoder().encode(JSON.stringify(rpc({ type: 'message_start', message: assistant(text) })) + '\n'))
    send('A', '过期的 A 输出')
    send('B', 'B 输出')
    await waitFor(() => w.messages.value.length === 1)
    assert.deepEqual(w.messages.value.map(m => m.text), ['B 输出'])
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
    assert.equal(w.messages.value.length, 0)
  } finally { app.unmount() }
})

test('components preserve sandbox and pure text rendering', async () => {
  const conversation = await readFile(resolve(root, 'src/components/ConversationPanel.vue'), 'utf8')
  assert.match(conversation, /!messages.length[^>]*>未开始/)
  assert.match(conversation, /等待 Agent 输出/)
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
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
    if (url === '/task/list_tasks') return response({ tasks: [{ ...task('A'), ip_name: 'EnglishIP', projectID: 'project-A', keti: 'keti2' }, { ...task('B'), ip_id: 'LegacyIP' }] })
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
    elements.find(el => el.tag === 'button' && el.text === '任务详情').props.onClick(); await nextTick()
    assert.ok(elements.some(el => el.tag === 'h2' && el.text === 'EnglishIP'))
    assert.ok(elements.some(el => el.tag === 'p' && el.text === 'projectID: project-A / taskID: A'))
    assert.ok(elements.some(el => el.tag === 'small' && el.text === 'A'))
    const danger = elements.find(el => el.props.class === 'task-danger')
    const remove = elements.find(el => el.tag === 'button' && el.text.trim() === '删除当前任务')
    assert.ok(danger)
    assert.equal(remove.props.disabled, false)
    assert.equal(remove.props['aria-label'], '永久删除任务 A')
    let confirmed = ''
    globalThis.window = { confirm: text => { confirmed = text; return false } }
    remove.props.onClick(); await nextTick()
    assert.match(confirmed, /永久删除任务「A」/)
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
    assert.ok(elements.some(el => el.tag === 'h2' && el.text === 'LegacyIP'))
    assert.ok(elements.some(el => el.tag === 'p' && el.text === 'projectID: — / taskID: B'))
    assert.equal(eventReads, 2)
  } finally {
    app.unmount()
    for (const { c } of streams.values()) c.close()
  }
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
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
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
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
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
    assert.deepEqual(f.w.messages.value.map(m => m.text), [])
    assert.equal(f.w.detailError.value, '')
    assert.equal(f.w.streamError.value, '')
    f.streams[0].c.enqueue(new TextEncoder().encode(JSON.stringify(rpc({ type: 'message_start', message: assistant('旧输出') })) + '\n'))
    oldList.resolve(response({ tasks: [f.task('A')] }))
    await refreshing
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['B'])
    freshList.resolve(response({ tasks: [f.task('A'), f.task('B')] }))
    await deleting
    assert.deepEqual(f.w.tasks.value.map(t => t.task_id), ['B'])
    assert.deepEqual(f.w.messages.value.map(m => m.text), [])
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

test('TaskSidebar 仅选择任务，名字独占主行，ID 和状态同行，删除错误可见', async () => {
  const selected = []
  const props = reactive({ tasks: [{ task_id: 'A', ip_name: 'LongEnglishIP', status: 'running' }], selectedId: 'A', loading: false,
    error: '', deletingId: '', deleteError: '', onSelect: id => selected.push(id) })
  const rootElement = {}
  const sidebarApp = renderer.createApp({ render: () => h(TaskSidebar, props) })
  sidebarApp.mount(rootElement)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  try {
    const select = nodes().find(el => el.props?.class === 'task-select')
    select.props.onClick()
    assert.deepEqual(selected, ['A'])
    assert.equal(nodes().filter(el => el.tag === 'button').length, 2)
    const meta = nodes().find(el => el.props?.class === 'task-meta')
    assert.ok(descendants(meta).some(el => el.tag === 'small' && el.text === 'A'))
    assert.ok(descendants(meta).some(el => el.text === '运行中'))
    props.deletingId = 'A'; props.deleteError = '永久删除失败：409'
    await nextTick()
    assert.equal(select.props.disabled, true)
    assert.ok(nodes().some(el => el.props?.role === 'alert' && el.text === props.deleteError))
  } finally { sidebarApp.unmount() }
})

test('删除时迟到的详情响应不恢复任务或启动事件订阅', async () => {
  const detail = deferred()
  const deletion = deferred()
  let signal, eventReads = 0
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
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
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
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
const { default: ProjectPanel } = await import(pathToFileURL(resolve(out, 'components/ProjectPanel.js')))
const projectApi = await import(pathToFileURL(resolve(out, 'projectApi.js')))
const { ref } = await import('vue')
const flushProject = async () => { for (let i = 0; i < 40; i++) await Promise.resolve(); await nextTick() }
function mountedProject(onChanged) {
  let project
  const active = ref(true)
  const app = renderer.createApp({ setup() { project = useProject(active, onChanged); return () => null } })
  app.mount({})
  return { app, p: project, active }
}
test('多轮显式 user 全量重放，event_id 去重，同文本不同轮和同轮均保留', () => {
  const state = initialConversation()
  const events = [
    { type: 'user', message: '初始', turn_id: 1, event_id: 1 },
    { ...rpc({ type: 'message_start', message: assistant('') }), turn_id: 1, event_id: 2 },
    { ...rpc({ type: 'message_update', assistantMessageEvent: { type: 'text_delta', delta: '回答' } }), turn_id: 1, event_id: 3 },
    { ...rpc({ type: 'message_end', message: assistant('回答') }), turn_id: 1, event_id: 4 },
    { type: 'user', message: '继续', turn_id: 2, event_id: 5 },
    { type: 'user', message: '继续', turn_id: 3, event_id: 6 },
    { type: 'user', message: '继续', turn_id: 3, event_id: 7 },
  ]
  for (const e of [...events, ...events]) applyTaskEvent(state, e)
  assert.deepEqual(state.items.map(m => m.text), ['初始', '回答', '继续', '继续', '继续'])
  assert.deepEqual(state.items.filter(m => m.kind === 'user').map(m => m.turnId), [1, 2, 3, 3])
})

test('初始 RPC 原文保留前缀，后续显式输入与 RPC 配对，不合并重复主动输入', () => {
  for (const explicitFirst of [false, true]) {
    const state = initialConversation()
    const original = '工作目录和 skill 前缀 原提示'
    assert.deepEqual(state.items, [])
    applyTaskEvent(state, rpc({ type: 'message_start', message: { role: 'user', content: original } }))
    applyTaskEvent(state, rpc({ type: 'message_end', message: { role: 'user', content: original } }))
    applyTaskEvent(state, rpc({ type: 'message_end', message: assistant('第一轮') }))
    const explicit = { type: 'user', message: '补充', turn_id: 2, event_id: 1 }
    if (explicitFirst) applyTaskEvent(state, explicit)
    applyTaskEvent(state, { ...rpc({ type: 'message_start', message: { role: 'user', content: [{ type: 'text', text: '补充' }] } }), turn_id: 2 })
    applyTaskEvent(state, { ...rpc({ type: 'message_end', message: { role: 'user', content: '补充' } }), turn_id: 2 })
    if (!explicitFirst) applyTaskEvent(state, explicit)
    applyTaskEvent(state, { ...explicit, event_id: 2 })
    applyTaskEvent(state, { ...rpc({ type: 'message_start', message: { role: 'user', content: '补充' } }), turn_id: 2 })
    applyTaskEvent(state, { ...rpc({ type: 'message_end', message: { role: 'user', content: '补充' } }), turn_id: 2 })
    assert.deepEqual(state.items.map(m => m.text), [original, '第一轮', '补充', '补充'])
  }
})

test('初始 RPC 后主动发送同文输入不被误合并', () => {
  const state = initialConversation()
  applyTaskEvent(state, { ...rpc({ type: 'message_end', message: { role: 'user', content: '相同输入' } }), turn_id: 1 })
  applyTaskEvent(state, { ...rpc({ type: 'message_start', message: assistant('回复') }), turn_id: 1 })
  applyTaskEvent(state, { type: 'user', message: '相同输入', turn_id: 1, event_id: 1 })
  assert.deepEqual(state.items.map(m => m.text), ['相同输入', '回复', '相同输入'])
})

test('只有 user message_end 时仍以原文创建首消息', () => {
  const state = initialConversation()
  applyTaskEvent(state, rpc({ type: 'message_end', message: { role: 'user', content: '<skill>完整展开</skill>\n工作目录\n真实输入' } }))
  assert.equal(state.items[0].text, '<skill>完整展开</skill>\n工作目录\n真实输入')
})

test('不同轮助手流与同名工具隔离，旧轮迟到输出不拼入新轮', () => {
  const state = initialConversation()
  for (const turn_id of [1, 2]) {
    applyTaskEvent(state, { ...rpc({ type: 'message_start', message: assistant('轮' + turn_id) }), turn_id })
    applyTaskEvent(state, { ...rpc({ type: 'tool_execution_start', toolCallId: 'same', toolName: 'bash' }), turn_id })
  }
  applyTaskEvent(state, { ...rpc({ type: 'message_update', assistantMessageEvent: { type: 'text_delta', delta: '旧增量' } }), turn_id: 1 })
  applyTaskEvent(state, { ...rpc({ type: 'tool_execution_end', toolCallId: 'same', result: '旧结果' }), turn_id: 1 })
  assert.deepEqual(state.items.filter(m => m.kind === 'assistant').map(m => m.text), ['轮1旧增量', '轮2'])
  assert.deepEqual(state.items.filter(m => m.kind === 'tool').map(m => m.state), ['success', 'running'])
})

function chatFixture() {
  const records = new Map(['A', 'B'].map(id => [id, {
    task_id: id, prompt: 'prompt-' + id, status: 'running', chatstatus: 'running', turn_id: 1,
    verification_status: 'completed', created_at: '',
  }]))
  const histories = new Map(['A', 'B'].map(id => [id, [{ type: 'user', message: 'prompt-' + id, turn_id: 1, event_id: 1 }]]))
  const streams = [], calls = []
  let controlHandler = async (url, body) => {
    const t = records.get(body.task_id)
    if (url.endsWith('pause_task')) t.status = t.chatstatus = 'paused'
    else {
      t.turn_id++; t.status = t.chatstatus = 'queued'
      const history = histories.get(body.task_id)
      history.push({ type: 'user', message: body.message, turn_id: t.turn_id, event_id: history.length + 1 })
    }
    return response({ task_id: t.task_id, status: t.status })
  }
  globalThis.window = { confirm: () => true }
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
    calls.push({ url, options })
    if (url === '/task/list_tasks') return response({ tasks: [...records.values()] })
    if (url === '/task/send_message' || url === '/task/pause_task') return controlHandler(url, JSON.parse(options.body))
    const id = new URL(url, 'http://local').searchParams.get('task_id')
    if (url.startsWith('/task/delete_task')) { records.delete(id); return response({ task_id: id, status: 'deleted' }) }
    if (url.startsWith('/task/get_task')) return response({ task: records.get(id), files: [{ path: id + '.html', kind: 'report_html', size: 10 }] })
    return new Response(new ReadableStream({ start(c) {
      streams.push({ id, c, signal: options.signal })
      for (const e of histories.get(id)) c.enqueue(new TextEncoder().encode(JSON.stringify(e) + '\n'))
    } }))
  }
  const { app, w } = mountedWorkbench()
  return { app, w, records, histories, streams, calls,
    setControl(fn) { controlHandler = fn },
    emit(id, e) { streams.filter(s => s.id === id).at(-1).c.enqueue(new TextEncoder().encode(JSON.stringify(e) + '\n')) },
    async select(id) { await w.refreshTasks(); void w.selectTask(id); await waitFor(() => w.task.value?.task_id === id && w.streamState.value === 'live') },
    close() { app.unmount(); for (const { c } of streams) { try { c.close() } catch { /* 已取消。 */ } } },
  }
}

test('聊天 API 请求体及 409 错误，暂停真实请求不以 abort 替代', async () => {
  const calls = []
  globalThis.fetch = async (url, options) => {
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] }); calls.push({ url, options }); return response({ task_id: 'A', status: 'paused' }) }
  await api.sendMessage('A', '补充')
  await api.pauseTask('A')
  assert.deepEqual(calls.map(c => [c.url, c.options.method, JSON.parse(c.options.body)]), [
    ['/task/send_message', 'POST', { task_id: 'A', message: '补充' }],
    ['/task/pause_task', 'POST', { task_id: 'A' }],
  ])
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: '资源忙' }), { status: 409 })
  await assert.rejects(api.sendMessage('A', '补充'), /资源忙/)
  await assert.rejects(api.pauseTask('A'), /资源忙/)
})

test('运行中允许发送补充，busy 禁重发，成功全量重连无重复，输入修改不被清空', async () => {
  const f = chatFixture(), late = deferred()
  try {
    await f.select('A'); f.w.draft.value = '补充'
    assert.equal(f.w.canSend.value, true)
    f.setControl(() => late.promise)
    const sending = f.w.sendMessage()
    assert.equal(f.w.chatBusy.value, 'send')
    assert.equal(f.w.canSend.value, false)
    await f.w.sendMessage(); await f.w.pauseTask()
    assert.equal(f.calls.filter(c => c.url === '/task/send_message').length, 1)
    f.w.draft.value = '下一条'
    f.histories.get('A').push({ type: 'user', message: '补充', turn_id: 1, event_id: 2 })
    late.resolve(response({ task_id: 'A', status: 'running' })); await sending
    await waitFor(() => f.streams.length === 2 && f.w.messages.value.length === 2)
    assert.equal(f.streams[0].signal.aborted, true)
    assert.deepEqual(f.w.messages.value.map(m => m.text), ['prompt-A', '补充'])
    assert.equal(f.w.draft.value, '下一条')
  } finally { f.close() }
})

test('暂停等待后端确认，暂停后与 idle/completed 原 task 继续，多轮历史完整', async () => {
  const f = chatFixture(), pausing = deferred()
  try {
    await f.select('A')
    f.setControl(() => pausing.promise)
    const request = f.w.pauseTask()
    assert.equal(f.w.chatBusy.value, 'pause')
    assert.equal(f.w.task.value.status, 'running')
    assert.equal(f.streams[0].signal.aborted, false)
    f.records.get('A').status = f.records.get('A').chatstatus = 'paused'
    pausing.resolve(response({ task_id: 'A', status: 'paused' })); await request
    await waitFor(() => f.streams.length === 2 && f.w.task.value?.status === 'paused')
    f.setControl(async (url, body) => {
      const task = f.records.get('A'); task.turn_id++; task.status = task.chatstatus = 'queued'
      const history = f.histories.get('A')
      history.push({ type: 'user', message: body.message, turn_id: task.turn_id, event_id: history.length + 1 })
      return response({ task_id: 'A', status: 'queued' })
    })
    for (const status of ['paused', 'idle', 'completed']) {
      f.w.task.value.status = status
      f.w.draft.value = '继续'
      const count = f.streams.length
      await f.w.sendMessage(); await waitFor(() => f.streams.length > count && f.w.streamState.value === 'live')
      assert.equal(f.w.selectedId.value, 'A')
      assert.equal(f.w.draft.value, '')
    }
    assert.deepEqual(f.w.messages.value.map(m => m.text), ['prompt-A', '继续', '继续', '继续'])
    assert.equal(f.w.task.value.verification_status, 'completed')
  } finally { f.close() }
})

test('旧 status/settled 不提前结束新轮，重复 status 忽略，迟到旧详情不盖新状态', async () => {
  const f = chatFixture()
  try {
    f.records.get('A').turn_id = 3
    f.histories.get('A').push({ type: 'status', status: 'completed', turn_id: 1, event_id: 2 })
    await f.select('A')
    assert.equal(f.w.task.value.status, 'running')
    const old = deferred(), mockFetch = globalThis.fetch
    globalThis.fetch = (url, options) => url.startsWith('/task/get_task') ? old.promise : mockFetch(url, options)
    const refreshing = f.w.refreshSelected()
    f.emit('A', { type: 'status', status: 'paused', turn_id: 3, event_id: 3 })
    await waitFor(() => f.w.task.value.status === 'paused')
    f.emit('A', { type: 'status', status: 'failed', turn_id: 3, event_id: 3 })
    f.emit('A', { ...rpc({ type: 'agent_settled' }), turn_id: 1, event_id: 4 })
    old.resolve(response({ task: { ...f.records.get('A'), status: 'running' }, files: [] }))
    await refreshing; await flushProject()
    assert.equal(f.w.task.value.status, 'paused')
    assert.equal(f.w.files.value[0].path, 'A.html')
  } finally { f.close() }
})

test('切任务隔离 send/pause 迟到成功与失败，不重连、不清草稿和新请求忙态', async () => {
  for (const action of ['send', 'pause']) for (const success of [true, false]) {
    const f = chatFixture(), late = deferred(), newRequest = deferred()
    try {
      await f.select('A'); f.w.draft.value = 'A草稿'
      f.setControl(() => late.promise)
      const old = action === 'send' ? f.w.sendMessage() : f.w.pauseTask()
      await f.select('B'); f.w.draft.value = 'B草稿'
      f.setControl(() => newRequest.promise)
      const current = f.w.sendMessage()
      if (success) late.resolve(response({ task_id: 'A', status: 'paused' }))
      else late.resolve(new Response(JSON.stringify({ detail: 'A迟到错误' }), { status: 409 }))
      await old; await flushProject()
      assert.equal(f.w.selectedId.value, 'B')
      assert.equal(f.w.draft.value, 'B草稿')
      assert.equal(f.w.chatBusy.value, 'send')
      assert.equal(f.w.chatError.value, '')
      assert.equal(f.streams.length, 2)
      newRequest.resolve(new Response(JSON.stringify({ detail: 'B错误' }), { status: 409 })); await current
      assert.equal(f.w.chatError.value, 'B错误')
      await f.select('A'); assert.equal(f.w.draft.value, 'A草稿')
    } finally { f.close() }
  }
})

test('删除与详情列表刷新后迟到聊天请求不能复活旧 task，草稿缺失任务清理', async () => {
  for (const reset of [false, true]) for (const action of ['send', 'pause']) {
    const f = chatFixture(), late = deferred()
    try {
      await f.select('A'); f.w.draft.value = 'A草稿'
      f.setControl(() => late.promise)
      const request = action === 'send' ? f.w.sendMessage() : f.w.pauseTask()
      if (reset) { f.records.delete('A'); await f.w.resetHistory() }
      else await f.w.removeTask('A')
      await waitFor(() => f.w.task.value?.task_id === 'B')
      f.w.draft.value = 'B草稿'
      late.resolve(response({ task_id: 'A', status: 'paused' })); await request; await flushProject()
      assert.equal(f.w.selectedId.value, 'B')
      assert.equal(f.w.draft.value, 'B草稿')
      assert.equal(f.w.chatError.value, '')
      assert.equal(f.calls.filter(c => c.url.startsWith('/task/get_task') && c.url.endsWith('=A')).length, 1)
    } finally { f.close() }
  }
})

test('详情列表刷新保留仍存在的当前 task 与草稿；无任务、created、空白禁止发送', async () => {
  const f = chatFixture()
  try {
    assert.equal(f.w.canSend.value, false); await f.w.sendMessage(); await f.w.pauseTask()
    await f.select('B'); f.w.draft.value = 'B草稿'
    await f.w.resetHistory(); await waitFor(() => f.w.task.value?.task_id === 'B')
    assert.equal(f.w.draft.value, 'B草稿')
    f.w.task.value.status = 'created'; assert.equal(f.w.canSend.value, false)
    f.w.task.value.status = 'running'; f.w.draft.value = '  '; assert.equal(f.w.canSend.value, false)
    assert.equal(f.calls.some(c => ['/task/send_message', '/task/pause_task'].includes(c.url)), false)
  } finally { f.close() }
})


test('实际聊天输入接线：模式/视图/切任务保留隔离草稿，发送忙态与错误展示', async () => {
  const originalDocument = globalThis.Document, originalShadowRoot = globalThis.ShadowRoot
  globalThis.Document = class {}; globalThis.ShadowRoot = class {}
  const f = chatFixture(), late = deferred()
  const rootElement = {}, app = renderer.createApp(App)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  const button = text => nodes().find(el => el.tag === 'button' && el.text === text)
  const input = () => nodes().find(el => el.props?.id === 'chat-message')
  const select = id => nodes().find(el => el.props?.class === 'task-select' && descendants(el).some(n => n.tag === 'strong' && n.text === id)).props.onClick()
  try {
    app.mount(rootElement); await waitFor(() => f.streams.length === 1); await nextTick()
    button('任务详情').props.onClick(); await nextTick()
    input().props.onInput({ target: { value: 'A草稿' } }); await nextTick()
    const composer = nodes().find(el => el.props?.id === 'project-prompt')
    composer.props['onUpdate:modelValue']('创建草稿')
    button('验证结果报告').props.onClick(); await nextTick()
    button('项目验证').props.onClick(); await nextTick()
    button('任务详情').props.onClick(); button('对话').props.onClick(); await nextTick()
    assert.equal(input().props.value, 'A草稿')
    assert.equal(composer.value, '创建草稿')
    select('B'); await waitFor(() => f.streams.length === 2); await nextTick()
    assert.equal(input().props.value, '')
    input().props.onInput({ target: { value: 'B草稿' } }); await nextTick()
    select('A'); await waitFor(() => f.streams.length === 3); await nextTick()
    assert.equal(input().props.value, 'A草稿')
    f.setControl(() => late.promise)
    nodes().find(el => el.tag === 'form' && el.props.class === 'chat-input').props.onSubmit({ preventDefault() {} })
    await nextTick()
    assert.equal(button('发送').props.disabled, true)
    assert.equal(button('暂停').props.disabled, true)
    assert.equal(f.streams.at(-1).signal.aborted, false)
    late.resolve(new Response(JSON.stringify({ detail: '发送暂不可用' }), { status: 409 }))
    await flushProject()
    assert.equal(input().props.value, 'A草稿')
    assert.ok(nodes().some(el => el.props?.role === 'alert' && el.text === '发送暂不可用'))
    assert.equal(button('发送').props.disabled, false)
    assert.equal(composer.value, '创建草稿')
  } finally {
    app.unmount(); f.close()
    globalThis.Document = originalDocument; globalThis.ShadowRoot = originalShadowRoot
  }
})

test('详情列表刷新期间迟到旧详情不复活旧文件，删除中发送暂停禁止', async () => {
  const f = chatFixture(), lateDetail = deferred(), lateDelete = deferred()
  try {
    await f.select('A'); f.w.draft.value = 'A草稿'
    const mockFetch = globalThis.fetch
    globalThis.fetch = (url, options) => url.startsWith('/task/get_task') && url.endsWith('=A') ? lateDetail.promise : mockFetch(url, options)
    const refreshing = f.w.refreshSelected()
    f.records.delete('A'); await f.w.resetHistory(); await waitFor(() => f.w.task.value?.task_id === 'B')
    lateDetail.resolve(response({ task: { task_id: 'A', status: 'completed', prompt: '旧', turn_id: 1 }, files: [{ path: 'old.html' }] }))
    await refreshing
    assert.equal(f.w.task.value.task_id, 'B')
    assert.equal(f.w.files.value[0].path, 'B.html')
    f.w.draft.value = 'B草稿'
    globalThis.fetch = (url, options) => url.startsWith('/task/delete_task') ? lateDelete.promise : mockFetch(url, options)
    const deleting = f.w.removeTask('B')
    assert.equal(f.w.canSend.value, false); assert.equal(f.w.canPause.value, false)
    await f.w.sendMessage(); await f.w.pauseTask()
    assert.equal(f.calls.some(c => ['/task/send_message', '/task/pause_task'].includes(c.url)), false)
    f.records.delete('B'); lateDelete.resolve(response({ task_id: 'B', status: 'deleted' })); await deleting
    assert.equal(f.w.selectedId.value, '')
  } finally { f.close() }
})


test('新轮完成读取报告不丢聊天消息，旧轮报告完成状态不能盖新轮', async () => {
  const f = chatFixture()
  try {
    await f.select('A'); f.w.draft.value = '继续验证'
    await f.w.sendMessage(); await waitFor(() => f.streams.length === 2 && f.w.streamState.value === 'live')
    f.emit('A', { type: 'status', status: 'completed', turn_id: 1, event_id: 10 })
    await flushProject()
    assert.equal(f.w.task.value.status, 'queued')
    f.emit('A', { ...rpc({ type: 'message_end', message: assistant('新的回答') }), turn_id: 2, event_id: 11 })
    f.records.get('A').status = f.records.get('A').chatstatus = 'completed'
    f.emit('A', { type: 'status', status: 'completed', turn_id: 2, event_id: 12 })
    f.streams.at(-1).c.close()
    await waitFor(() => f.w.streamState.value === 'closed' && f.w.task.value.status === 'completed')
    assert.deepEqual(f.w.messages.value.map(m => m.text), ['prompt-A', '继续验证', '新的回答'])
    assert.equal(f.w.files.value[0].path, 'A.html')
  } finally { f.close() }
})


test('项目任务的暂停和普通聊天状态有明确标签', async () => {
  const { statusLabel } = await import(pathToFileURL(resolve(out, 'types.js')))
  assert.equal(statusLabel('paused'), '已暂停')
  assert.equal(statusLabel('idle'), '对话结束')
})



function projectClock() {
  const originalSet = globalThis.setTimeout, originalClear = globalThis.clearTimeout
  const timers = new Map()
  let serial = 0
  globalThis.setTimeout = (callback, delay) => { assert.equal(delay, 2000); timers.set(++serial, callback); return serial }
  globalThis.clearTimeout = id => timers.delete(id)
  return { timers, tick() { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach(fn => fn()) },
    restore() { globalThis.setTimeout = originalSet; globalThis.clearTimeout = originalClear } }
}

test('列表查询编码项目及任务 ID，空查询不推断来源', async () => {
  const urls = []
  globalThis.fetch = async url => { urls.push(url); return response({ tasks: [] }) }
  await api.listTasks('项目 /#', 'a b')
  const query = new URL(urls[0], 'http://local').searchParams
  assert.equal(query.get('projectID'), '项目 /#')
  assert.equal(query.get('task_id'), 'a b')
  assert.equal(query.has('keti'), false)
  await api.listTasks()
  assert.equal(urls[1], '/task/list_tasks')
})

test('projectID 查询保留不同 timestamp 批次和同批多个 IP，不发批次过滤', async () => {
  const calls = [], tasks = [
    { task_id: 'a', projectID: 'P', timestamp: '2026-10-14 01:02:03.000001' },
    { task_id: 'b', projectID: 'P', timestamp: '2026-10-14 01:02:03.000001' },
    { task_id: 'c', projectID: 'P', timestamp: '2026-10-14 01:02:03.000002' },
  ]
  globalThis.fetch = async url => {
    if (url === '/task/list_dataset') return response({ ips: [], tools: [] })
    calls.push(url); return response({ tasks })
  }
  const { app, p } = mountedProject()
  try {
    p.queryID.value = 'P'; await p.refresh()
    assert.deepEqual(p.tasks.value, tasks)
    assert.equal(calls.length, 1)
    const query = new URL(calls[0], 'http://local').searchParams
    assert.equal(query.get('projectID'), 'P')
    assert.equal(query.has('timestamp'), false)
  } finally { app.unmount() }
})

test('local 自动任务 ID，三工具与空提示词；换类别/IP 不写入模板', async () => {
  const clock = projectClock(), calls = []
  let changes = 0
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options })
    if (url === '/task/list_dataset') return response({ ips: [{ ip_name: 'AttiCal' }, { ip_name: 'Other' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
    if (url === '/task/create_task') return response({ task_id: 'auto1234', status: 'queued' })
    return response({ tasks: [] })
  }
  const { app, p } = mountedProject(() => changes++)
  try {
    await flushProject()
    assert.equal(p.source.value, 'local')
    assert.deepEqual(p.dataset.value, ['AttiCal', 'Other'])
    assert.equal(p.prompt.value, '')
    p.ip.value = 'AttiCal'; p.tool.value = 'KLEE'
    await p.submit()
    const body = JSON.parse(calls.find(c => c.url === '/task/create_task').options.body)
    assert.deepEqual(body, { ip_name: 'AttiCal', tool: 'KLEE', userprompt: '' })
    assert.equal(changes, 1)
    p.source.value = 'keti3'; p.source.value = 'local'; p.ip.value = 'Other'
    assert.equal(p.prompt.value, '')
  } finally { app.unmount(); clock.restore() }
})

test('同项目重复提交无确认无删除，忙时防重，后端生成批次时间戳', async () => {
  const clock = projectClock(), calls = [], pending = deferred()
  let changes = 0
  globalThis.window = { confirm: () => assert.fail('重复提交不应确认') }
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options })
    if (url === '/task/list_dataset') return response({ ips: [], tools: [] })
    if (url === '/project/create_project') return calls.filter(c => c.url === url).length === 1
      ? pending.promise : response({ projectID: '123', keti: 'keti3', timestamp: '2026-10-14 01:02:03.000002', status: 'accepted' })
    assert.fail(`意外请求：${url}`)
  }
  const { app, p } = mountedProject(() => changes++)
  try {
    await flushProject()
    p.source.value = 'keti3'; p.projectID.value = '123'; p.prompt.value = '用户要求'; p.tool.value = 'KLEE'
    const creating = p.submit()
    await p.submit()
    assert.equal(calls.filter(c => c.url === '/project/create_project').length, 1)
    pending.resolve(response({ projectID: '123', keti: 'keti3', timestamp: '2026-10-14 01:02:03.000001', status: 'accepted' }))
    await creating
    await p.submit()
    const submissions = calls.filter(c => c.url === '/project/create_project')
    assert.equal(submissions.length, 2)
    for (const call of submissions) assert.deepEqual(JSON.parse(call.options.body), {
      projectID: '123', source: 'keti3', userprompt: '用户要求', tool: 'KLEE',
    })
    assert.equal(changes, 2)
    assert.equal(p.projectID.value, '123')
    assert.equal(p.prompt.value, '用户要求')
    assert.equal(calls.some(c => /delete|list_tasks/.test(c.url)), false)
    assert.equal('forceSubmit' in p, false)
    assert.equal('removeProject' in p, false)
    assert.equal('deleteProject' in projectApi, false)
  } finally { app.unmount(); clock.restore() }
})

test('项目列表仅手动查询，挂载激活提交不请求，无轮询，迟到响应隔离', async () => {
  const clock = projectClock(), old = deferred(), calls = []
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_dataset') return response({ ips: [], tools: [] })
    if (url === '/task/create_task') return response({ task_id: 'created' })
    calls.push({ url, signal: options.signal })
    return calls.length === 1 ? old.promise : response({ tasks: [{ task_id: 'new', projectID: 'P', keti: null }] })
  }
  const { app, p, active } = mountedProject()
  try {
    await flushProject()
    assert.equal(calls.length, 0)
    active.value = false; active.value = true; await flushProject()
    assert.equal(calls.length, 0)
    p.ip.value = 'AttiCal'; await p.submit()
    assert.equal(calls.length, 0)
    const first = p.refresh()
    p.queryID.value = 'P'; await p.refresh()
    old.resolve(response({ tasks: [{ task_id: 'old' }] })); await first
    assert.equal(calls[0].signal.aborted, true)
    assert.equal(p.tasks.value[0].task_id, 'new')
    assert.equal(clock.timers.size, 0)
    active.value = false; active.value = true; await flushProject()
    assert.equal(calls.length, 2)
    assert.equal(p.tasks.value[0].keti, null)
    await p.refresh()
    assert.equal(calls.length, 3)
    app.unmount()
    assert.equal(clock.timers.size, 0)
  } finally { app.unmount(); clock.restore() }
})

test('实际统一提交组件：点击才填模板、缺目录提示、NULL 项目与来源、查看详情', async () => {
  const originalDocument = globalThis.Document, originalShadowRoot = globalThis.ShadowRoot
  globalThis.Document = class {}; globalThis.ShadowRoot = class {}
  const clock = projectClock(), rootElement = {}, viewed = []
  globalThis.fetch = async url => url === '/task/list_dataset'
    ? response({ ips: [{ ip_name: 'AttiCal' }], tools: ['CBMC', 'CPAchecker', 'KLEE'] })
    : response({ tasks: [
      { task_id: 'local01', timestamp: null, projectID: null, keti: null, ip_name: 'AttiCal', status: 'completed' },
      { task_id: 'missing1', timestamp: '2026-10-14 00:00:00', projectID: '123', keti: 'keti2', ip_name: 'IP', status: 'missing', missing_directory: true },
    ] })
  const app = renderer.createApp({ setup() { return () => h(ProjectPanel, { active: true, onViewTask: id => viewed.push(id) }) } })
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  try {
    app.mount(rootElement); await flushProject()
    assert.equal(nodes().filter(n => n.tag === 'button' && n.text === '查看详情').length, 0)
    nodes().find(n => n.tag === 'button' && n.text === '全部').props.onClick(); await flushProject()
    const prompt = nodes().find(n => n.props?.id === 'project-prompt')
    assert.equal(prompt.value, '')
    for (const source of ['local', 'keti2', 'keti3', 'local']) {
      nodes().find(n => n.props?.id === 'project-source').props['onUpdate:modelValue'](source); await nextTick()
      assert.ok(nodes().some(n => n.props?.id === 'verify-tool'))
      assert.ok(!nodes().some(n => n.tag === 'button' && /强制提交|删除项目/.test(n.text || '')))
      assert.ok(!nodes().some(n => /默认使用 CBMC；|无需项目 ID，任务 ID 自动生成/.test(n.text || '')))
    }
    const ip = nodes().find(n => n.props?.id === 'dataset-ip')
    ip.props['onUpdate:modelValue']('AttiCal'); await nextTick()
    assert.equal(prompt.value, '')
    nodes().find(n => n.tag === 'button' && n.text.includes('点击填入')).props.onClick(); await nextTick()
    assert.match(prompt.value, /仅执行一个 case/)
    assert.match(prompt.value, /<input>\/ = \/app\/vip4\/tasks\/<task_id>\/input\//)
    assert.doesNotMatch(prompt.value, /dataset/)
    assert.ok(nodes().some(n => n.tag === 'td' && descendants(n).some(child => child.text === '—')))
    assert.ok(nodes().some(n => n.tag === 'th' && n.text === 'timestamp（UTC）'))
    assert.ok(nodes().some(n => n.tag === 'td' && n.text === '2026-10-14 00:00:00'))
    assert.ok(nodes().some(n => n.tag === 'td' && n.text === '实际目录已删除'))
    assert.equal(nodes().filter(n => n.props?.class === 'source-tag').length, 1)
    const buttons = nodes().filter(n => n.tag === 'button' && n.text === '查看详情')
    assert.equal(buttons[1].props.disabled, true)
    buttons[0].props.onClick()
    assert.deepEqual(viewed, ['local01'])
  } finally { app.unmount(); clock.restore(); globalThis.Document = originalDocument; globalThis.ShadowRoot = originalShadowRoot }
})

test('旧创建 UI 已移除，详情仅保留视图，整任务 ZIP 与单文件下载并存', async () => {
  const app = await readFile(resolve(root, 'src/App.vue'), 'utf8')
  const artifacts = await readFile(resolve(root, 'src/components/ArtifactPanel.vue'), 'utf8')
  assert.match(app, /@changed="resetHistory"/)
  assert.doesNotMatch(app, /@forced/)
  assert.match(app, /ref<'single' \| 'project'>\('project'\)/)
  assert.doesNotMatch(app, /TaskComposer|createError|creating|@submit="submit"/)
  await assert.rejects(readFile(resolve(root, 'src/components/TaskComposer.vue')), { code: 'ENOENT' })
  assert.match(artifacts, /taskZipUrl\(taskId\)/)
  assert.match(artifacts, /fileUrl\(taskId, file.path, true\)/)
})

test('IP 标识保持英文，历史回退；两栏填满视口，四按钮始终竖列', async () => {
  const { ipLabel } = await import(pathToFileURL(resolve(out, 'types.js')))
  assert.equal(ipLabel({ task_id: 'old', ip_name: 'AttiCal', ip_id: 'id' }), 'AttiCal')
  assert.equal(ipLabel({ task_id: 'old', ip_name: '', ip_id: 'EnglishID' }), 'EnglishID')
  assert.equal(ipLabel({ task_id: 'old' }), 'old')
  const css = await readFile(resolve(root, 'src/style.css'), 'utf8')
  const controls = [...css.matchAll(/\.view-controls\s*\{([^}]+)\}/g)]
  assert.equal(controls.length, 1)
  assert.match(controls[0][1], /flex-direction:column/)
  assert.doesNotMatch(controls[0][1], /grid-template-columns/)
  assert.match(css, /\.project-panel \{[^}]*flex:1; min-height:0;[^}]*align-items:stretch/)
  assert.match(css, /\.project-input,\.project-output \{[^}]*min-height:0; overflow:auto/)
  assert.match(css, /grid-template-rows:minmax\(0,1fr\) minmax\(0,1fr\)/)
})

test('远程普通提交传工具，初始默认为 CBMC', async () => {
  const calls = []
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_dataset') return response({ ips: [], tools: [] })
    calls.push(JSON.parse(options.body)); return response({ status: 'accepted' })
  }
  const { app, p } = mountedProject()
  try {
    assert.equal(p.tool.value, 'CBMC')
    for (const source of ['keti2', 'keti3']) {
      p.source.value = source; p.projectID.value = '123'
      for (const tool of ['CBMC', 'CPAchecker', 'KLEE']) {
        p.tool.value = tool; await p.submit()
        assert.deepEqual(calls.at(-1), { projectID: '123', source, userprompt: '', tool })
      }
    }
  } finally { app.unmount() }
})

test('右栏删除当前任务：无选择禁用、忙态防重、错误保留与成功清空', async () => {
  const rootElement = {}, streams = [], requests = [], confirmations = []
  let listing = [], pending = deferred()
  globalThis.window = { confirm: text => { confirmations.push(text); return true } }
  globalThis.fetch = async (url, options = {}) => {
    if (url === '/task/list_dataset') return response({ ips: [], tools: [] })
    if (url === '/task/list_tasks') return response({ tasks: listing })
    if (options.method === 'DELETE') { requests.push(url); return pending.promise }
    if (url.startsWith('/task/get_task')) return response({ task: listing[0], files: [] })
    return new Response(new ReadableStream({ start(c) { streams.push(c) } }))
  }
  const app = renderer.createApp(App)
  const descendants = node => [node, ...(node.children || []).flatMap(descendants)]
  const nodes = () => descendants(rootElement)
  const remove = () => nodes().find(n => n.tag === 'button' && n.props['aria-label']?.startsWith('永久删除任务'))
  try {
    app.mount(rootElement); await nextTick()
    assert.equal(nodes().find(n => n.tag === 'button' && n.text.trim() === '删除当前任务').props.disabled, true)
    listing = [{ task_id: 'A', status: 'running', prompt: '' }]
    await waitFor(() => nodes().some(n => n.props?.['aria-label'] === '刷新任务列表' && !n.props.disabled))
    nodes().find(n => n.props?.['aria-label'] === '刷新任务列表').props.onClick()
    await waitFor(() => nodes().some(n => n.props?.class === 'task-select'))
    nodes().find(n => n.props?.class === 'task-select').props.onClick()
    await waitFor(() => remove()?.props.disabled === false)
    remove().props.onClick(); await nextTick()
    assert.equal(remove().props.disabled, true)
    assert.equal(remove().props['aria-busy'], true)
    assert.equal(remove().text.trim(), '删除中…')
    remove().props.onClick()
    assert.equal(requests.length, 1)
    pending.resolve(new Response(JSON.stringify({ detail: '测试删除失败' }), { status: 409 }))
    await waitFor(() => remove()?.props.disabled === false)
    assert.ok(nodes().some(n => n.props?.role === 'alert' && n.text.includes('测试删除失败')))
    assert.ok(nodes().some(n => n.props?.class === 'task-select'))
    pending = deferred()
    remove().props.onClick(); await nextTick()
    pending.resolve(response({ task_id: 'A', status: 'deleted' }))
    await waitFor(() => !remove())
    assert.equal(nodes().find(n => n.tag === 'button' && n.text.trim() === '删除当前任务').props.disabled, true)
    assert.equal(requests.length, 2)
    assert.equal(confirmations.length, 2)
    assert.ok(confirmations.every(text => text.includes('永久删除任务「A」')))
  } finally { app.unmount(); for (const c of streams) { try { c.close() } catch {} } }
})
