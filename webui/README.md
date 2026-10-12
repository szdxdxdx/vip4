# VIP4 Agent 验证工作台

Vue 3 + TypeScript，无路由、无额外 UI 依赖。仅使用 `/task` API。

```sh
npm run dev    # Vite 默认本机监听；/task 开发代理到 127.0.0.1:8414
npm run build  # vue-tsc + Vite
npm test       # 无浏览器测试，所有 HTTP 请求均使用 mock，不调用 LLM
```

生产部署须由同源服务将 `/task` 转发到后端；Vite proxy 仅在开发时生效。

## 结构

- `src/App.vue`：工作台布局和组件接线。
- `src/components/TaskSidebar.vue`：任务列表、刷新和选择。
- `src/components/ConversationPanel.vue`：会话视图、靠近底部才自动滚动。
- `src/components/MessageItem.vue`：纯文本消息、折叠思考和工具卡片。
- `src/components/TaskComposer.vue`：手动任务 ID、新建提示词和模板恢复。
- `src/components/ArtifactPanel.vue`：报告自动选择、隔离 iframe 预览、原生 dialog 展开阅读、文件下载。
- `src/composables/useWorkbench.ts`：任务选择、AbortController、竞态隔离、结束后元数据重试。
- `src/composables/eventReducer.ts`：Pi RPC 到显示模型的增量归约，不保存原始 events。
- `src/api.ts`：请求、错误 detail、NDJSON 读取和编码后的文件链接。
- `src/types.ts`：API/显示类型和状态标签。
- `src/templates/attical.ts`：保留原有 AttiCal 提示词，提交时替换 `<task_id>`。
- `tests/workbench.test.mjs`：实际 TS 模块的归约/流/竞态测试，以及静态安全约束检查。

切换任务会中断旧订阅，不调用任何后端取消 API。每次选择任务从 metadata 初始化一次用户提示词，再完整回放事件；Pi 用户消息和控制事件不作为独立消息显示。工具输出/参数最多显示 24,000 字符，原文件可在产物栏下载。

任务 status 以 metadata 为准，流关闭不代表任务完成。流结束后刷新列表、详情和产物，短延迟重试解决最终 metadata 提交的竞态。连接异常可点击“重新加载”重新回放。

报告仅从详情 API 的 `files` 中按 `kind: report_html` 选择；文件路径不推断。iframe 使用 `sandbox="allow-scripts"`，没有 `allow-same-origin`；消息、思考和工具内容均使用 Vue 文本插值。

测试不等价于浏览器或真实后端验证。真实报告的交互及视觉效果需在后端运行时使用浏览器验证。
