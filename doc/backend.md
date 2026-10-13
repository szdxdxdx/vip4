# 后端项目验证

## 启动与接口

在 `server/` 执行 `uv run main.py --backend-only`。使用单进程部署，队列及验证资源锁在进程内共享。任务与项目接口均无 `/api` 前缀；若部署代理添加前缀，应同时代理下载链接。

- `POST /project/create_project`：正文 `{ "projectID": "项目标识", "prompt": "可选验证要求", "force": false, "source": "keti2" }`。普通提交立即返回 HTTP 202、`{projectID,status:"accepted"}`，后台查询并准备输入；已有项目返回 HTTP 409。

  `force=true` 表示永久替换：停止旧项目编排及其验证/聊天，等待输入收集和 Pi 资源释放，删除该项目全部任务目录和数据库映射，再重新查询并验证。响应 202 前完成旧数据清理，期间进度为 resetting，同项目的并发提交或删除返回 409。不存在的项目也可强制提交。请求断开不取消已接受的清理；删除失败保留旧映射、返回错误并允许再次强制提交，不启动新验证。其他项目和手动任务不受影响。
- `POST /project/delete_project`：正文 `{ "projectID": "项目标识" }`，成功返回 HTTP 200、`{projectID,status:"deleted"}`。永久删除该项目所有任务目录、SQLite 映射及项目/任务缓存。先停止原编排，等待查询和输入收集结束、验证/聊天停止并释放 Pi 资源；期间进度为 deleting，同项目的删除、普通提交或 force 返回 409。未知项目返回 404。请求断开或重复取消不打断清理；服务关闭会等待已接受的清理。删除失败保留全部映射，进度为 failed（不会被旧 completed 任务覆盖），可再次删除或 force 重试；权限错误返回 403，文件删除错误返回 500。部分已删除目录无需恢复，重试会跳过不存在的任务。成功后项目查询返回 404，可重新提交同 ID；其他项目和人工任务不受影响。
- `GET /project/get_progress?projectID=...`：返回 `{projectID,status,error?,total,finished,tasks:[{task_id,ip_id,status,created_at,...}]}`。`finished` 包含 completed、failed、cancelled、deleted 的任务。进度仅读取任务元数据，不扫描产物。
- `GET /project/get_results?projectID=...`：返回 `{projectID,tasks:[{task_id,ip_id,status,files:[{path,size,kind,download_url}]}]}`。只返回 `output` 目录中的文件，包含 SKILL 的 `cbmc_suite/output/` 等工具目录；不返回 input、会话、驱动及非 output 产物。`path` 相对任务 workspace，`download_url` 复用 `/task/get_file?task_id=...&path=...&download=true`。

未知项目返回 HTTP 404，空白标识返回 HTTP 422。项目状态为 accepted、resetting、deleting、collecting、running、completed、failed、cancelled、empty。查询结果为空时为 empty、total=0，不创建任务。查询失败为 failed，并返回 error。

## 输入与执行

`source` 仅接受 `keti2`、`keti3`，省略时为 `keti2`，非法值返回 422。来源决定项目查询和文件收集适配器；课题三查询返回标准合成 IP，业务 id 为 `keti3:<projectID>`，验证要求与用户 prompt 合并，课题二提示词保持不变。所有任务准备结束后才串行运行。项目 ID 在两来源间全局唯一，跨来源普通重复提交返回 409，force 可清理后切换来源。运行期进度可返回 source，SQLite 不保存来源，冷启动不推测历史项目来源。

默认查询接口为 `http://8.130.30.48:8877/api/search/searchSoftwareIPByProjectId`，projectId 使用字符串查询参数。响应必须为顶层 code=0、result 列表，每项包含 ipId。

仅收集以下字段的非空、非“无”文件来源；字段可为字符串或字符串列表：

- `ipMsg.entity.entityImplementation.dotC`、`dotH`
- `ipMsg.formalModel.stateMachine`、`contracts`、`nonfunctionalConstraint`、`invariant`

字段表示文件来源，不视为正文。优先使用显式路径映射和可读本机文件；不可读时调用课题二 `POST http://8.130.30.48:8877/api/file/downloadFile`，请求头 `Content-Type: application/json`，UTF-8 JSON 正文为 `{ "filePath": "原始文件路径" }`，不拼接路径或改变中文内容。响应文件字节流直接保存到 input；HTTP 下载错误使该任务输入准备失败。HTTP(S) URL 来源仍直接使用 GET 下载。

每个 IP 对应一个任务，任务 ID 为 MMDD 四位日期加四位小写字母/数字，碰撞时重试。普通任务删除保留已登记的项目任务 ID，人工入口不能复用，以免污染项目归属；强制提交则同时移除这些数据库记录。输入复制到 `tasks/<task_id>/input/`，C/H 保持同目录，保留 basename，重名加编号避免覆盖。`files.csv` 记录 ipId、原始 source、完整 field 和实际绝对 path；每个文件成功保存后追加记录，准备失败时保留已收集文件的清单，不修改原文件。

所有 IP 完成准备后才开始验证。单条输入准备失败标记 failed，其他 IP 继续。项目任务通过 TaskManager 与手动任务共用串行锁；删除单个运行任务不会跳过剩余任务。输入收集属于任务生命周期，删除会先等待收集线程退出，再删除整个目录，避免复制与删除并行。默认提示词要求使用 verify-ip SKILL 和 CBMC，明确 input、files.csv 位置，报告、驱动及配置遵循 SKILL 的目录约定。可选 prompt 作为附加要求。

## 任务对话

单个任务对应一个持久 Pi 会话。`POST /task/send_message` 接收 `{task_id,message}`，返回 HTTP 202、`{task_id,status}`；运行中发送的消息作为后续补充排队，轮次结束后继续对话。已结束或暂停的任务重新进入全局串行队列，显式加载本任务的会话文件恢复上下文，不读取其他任务的会话。输入准备期间不接受对话。

`POST /task/pause_task` 接收 `{task_id}`，等待当前输出停止并释放 Pi 资源后返回 `{task_id,status:"paused"}`。排队中的任务也可暂停；暂停不是删除，继续发送消息即可恢复上下文。页面断开或切换任务仅中断订阅，不会暂停后端执行。

任务 status/chatstatus 表示当前聊天状态，支持 queued、running、paused、idle、completed、failed、cancelled。idle 表示正常对话结束但未新生成报告；completed 表示本轮生成了有效的新验证报告。verification_status 保留最近验证状态，项目进度按该字段汇总，普通聊天不能把已有验证结论改成失败。首次验证没有有效报告仍判定 failed。

`GET /task/get_events` 重放本任务的完整历史并继续推送当前输出，格式为 NDJSON。用户消息为 `{type:"user",message,turn_id,event_id}`，助手及工具为 `{type:"agent",data,turn_id,event_id}`，状态为 `{type:"status",status,turn_id,event_id}`。event_id 用于去重，turn_id 区分轮次；历史 Pi 会话仍可回放。事件记录和 Pi 上下文都在任务目录中，删除任务会一并删除。

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

SQLite 保存 task_id、projectID 和 ip_id。ip_id 只取 `ipMsg.entity.basicInformation.id`（如 `B_TcProcess`），不同于数字 `ipId`，不保存 basicInformation 的 name 或其他字段；项目进度及结果列表均返回该标识，普通任务删除后仍保留归属和标识，强制提交会删除旧项目的所有映射。缺失或非字符串 id 记录为空字符串，不影响验证。

已有数据库启动时自动补充 ip_id 列，历史记录保留；历史任务未保存过该字段，值为空，页面显示“未提供 IP 标识”，不推测或重新查询补齐。数据库不保存项目状态、提示词或输入。重启后可通过映射查询历史任务及结果；TaskManager 将未完成的 created/queued/running 任务落盘为 cancelled，不自动恢复执行。正常关闭时先等待已接受的删除或 force 清理，再取消项目编排及剩余准备任务、释放任务资源并关闭 SQLite；关闭期间不启动新的项目验证。空项目或查询失败且尚未生成映射的项目只在内存中存在，重启后不可查询或保留重复提交限制。

日志包含时间、模块、级别。HTTP 记录方法、路径、状态码和耗时，不记录请求正文、查询参数或提示词；流式接口耗时表示建立响应所需时间。文件来源及编排模块使用独立模块日志。

## 测试

在 `server/` 执行 `uv run python -m unittest discover -s tests -v`。项目测试 mock 网络与 Pi，使用临时目录和 SQLite，不调用真实 LLM 或项目服务。
