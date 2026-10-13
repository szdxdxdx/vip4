# 后端项目验证

## 启动与接口

在 `server/` 执行 `uv run main.py --backend-only`。使用单进程部署，队列及验证资源锁在进程内共享。任务与项目接口均无 `/api` 前缀；若部署代理添加前缀，应同时代理下载链接。

- `POST /project/create_project`：正文 `{ "projectID": "项目标识", "prompt": "可选验证要求" }`。立即返回 HTTP 202、`{projectID,status:"accepted"}`，后台查询并准备输入。相同项目在本次服务进程内不得重复提交；有持久任务映射的项目即使已完成或任务已删除，仍返回 HTTP 409，防止重复验证。
- `GET /project/get_progress?projectID=...`：返回 `{projectID,status,error?,total,finished,tasks:[{task_id,status,created_at,...}]}`。`finished` 包含 completed、failed、cancelled、deleted 的任务。进度仅读取任务元数据，不扫描产物。
- `GET /project/get_results?projectID=...`：返回 `{projectID,tasks:[{task_id,status,files:[{path,size,kind,download_url}]}]}`。只返回 `output` 目录中的文件，包含 SKILL 的 `cbmc_suite/output/` 等工具目录；不返回 input、会话、驱动及非 output 产物。`path` 相对任务 workspace，`download_url` 复用 `/task/get_file?task_id=...&path=...&download=true`。

未知项目返回 HTTP 404，空白标识返回 HTTP 422。项目状态为 accepted、collecting、running、completed、failed、cancelled、empty。查询结果为空时为 empty、total=0，不创建任务。查询失败为 failed，并返回 error。

## 输入与执行

默认查询接口为 `http://8.130.30.48:8877/api/search/searchSoftwareIPByProjectId`，projectId 使用字符串查询参数。响应必须为顶层 code=0、result 列表，每项包含 ipId。

仅收集以下字段的非空、非“无”文件来源；字段可为字符串或字符串列表：

- `ipMsg.entity.entityImplementation.dotC`、`dotH`
- `ipMsg.formalModel.stateMachine`、`contracts`、`nonfunctionalConstraint`、`invariant`

字段表示文件来源，不视为正文。优先使用显式路径映射和可读本机文件；不可读时调用课题二 `POST http://8.130.30.48:8877/api/file/downloadFile`，请求头 `Content-Type: application/json`，UTF-8 JSON 正文为 `{ "filePath": "原始文件路径" }`，不拼接路径或改变中文内容。响应文件字节流直接保存到 input；HTTP 下载错误使该任务输入准备失败。HTTP(S) URL 来源仍直接使用 GET 下载。

每个 IP 对应一个任务，任务 ID 为 MMDD 四位日期加四位小写字母/数字，碰撞时重试。已登记的项目任务 ID 永久保留，即使删除任务，人工入口也不能复用该 ID，以免污染项目归属。输入复制到 `tasks/<task_id>/input/`，C/H 保持同目录，保留 basename，重名加编号避免覆盖。`files.csv` 记录 ipId、原始 source、完整 field 和实际绝对 path；每个文件成功保存后追加记录，准备失败时保留已收集文件的清单，不修改原文件。

所有 IP 完成准备后才开始验证。单条输入准备失败标记 failed，其他 IP 继续。项目任务通过 TaskManager 与手动任务共用串行锁；删除单个运行任务不会跳过剩余任务。输入收集属于任务生命周期，删除会先等待收集线程退出，再删除整个目录，避免复制与删除并行。默认提示词要求使用 verify-ip SKILL 和 CBMC，明确 input、files.csv 位置，报告、驱动及配置遵循 SKILL 的目录约定。可选 prompt 作为附加要求。

## 配置

启动前设置环境变量：

| 变量 | 默认值与用途 |
| --- | --- |
| `VIP_PROJECT_SEARCH_URL` | 上述项目查询接口，可用于测试或替换部署端点 |
| `VIP_SOURCE_PATH_MAP` | `{}`，JSON 路径前缀到本机目录的映射；优先匹配最长前缀，拒绝越界 |
| `VIP_SOURCE_DOWNLOAD_URL` | `http://8.130.30.48:8877/api/file/downloadFile`，课题二 POST 下载接口；设为空字符串可禁用路径下载，仅使用本机文件或直接 URL |
| `VIP_SOURCE_TIMEOUT` | `30`，网络请求超时秒数 |
| `VIP_PROJECT_DB` | 项目根目录 `projects.sqlite3`，SQLite 文件位置 |

例如，`VIP_SOURCE_PATH_MAP='{"/uploads":"/data/uploads"}'` 将远端返回的 `/uploads/ip.c` 映射到 `/data/uploads/ip.c`。如需切换文件服务地址，设置 `VIP_SOURCE_DOWNLOAD_URL`；服务应接收上述 POST JSON 正文并返回文件字节流。

SQLite 只保存 task_id/projectID 映射，不保存项目状态、提示词或输入。重启后可通过映射查询历史任务及结果；TaskManager 将未完成的 created/queued/running 任务落盘为 cancelled，不自动恢复执行。正常关闭时先取消项目编排及剩余准备任务，再释放任务资源。空项目或查询失败且尚未生成映射的项目只在内存中存在，重启后不可查询或保留重复提交限制。

日志包含时间、模块、级别。HTTP 记录方法、路径、状态码和耗时，不记录请求正文、查询参数或提示词；流式接口耗时表示建立响应所需时间。文件来源及编排模块使用独立模块日志。

## 测试

在 `server/` 执行 `uv run python -m unittest discover -s tests -v`。项目测试 mock 网络与 Pi，使用临时目录和 SQLite，不调用真实 LLM 或项目服务。
