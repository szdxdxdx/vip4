# 后端验证服务

## 启动与数据

在 `server/` 执行 `uv run main.py --backend-only`，不加该参数则同时提供编译后的前端。使用单进程部署：验证和续聊共用串行资源锁，所有 HTTP 路径无 `/api` 前缀。

任务目录为 `tasks/<task_id>/`，包含只读 `input/`、来源清单 `files.csv`、`task.json`、Pi 会话 `pi_session/` 和工作目录 `workspace/`。ID 自动分配为 MMDD 加四位随机字母/数字，目录、缓存或数据库碰撞均重新生成，不覆盖旧任务。SQLite `project_tasks` 只保存 `task_id`、`projectID`、`ip_id`、`keti` 和 `timestamp`；IP 名称和工具写入任务元数据，不放入数据库。

`keti` 为 keti2、keti3 或 NULL；本地任务的 keti 和 projectID 均为 NULL。同 `(keti, projectID)` 可重复提交，每次保留独立批次。后端以 UTC 生成 `YYYY-MM-DD HH:mm:ss.ffffff` 格式 timestamp，单进程内严格递增，同批多 IP 共用；新本地任务也生成 timestamp，写入数据库和 task.json。查询以 `(keti, projectID)` 区分来源，删除仅以 task_id 为唯一标识。

旧数据库启动时迁移为允许 projectID=NULL 的结构，缺失来源保持 NULL，不推断归类。仅在 timestamp 字段缺失时将已有记录补为固定 `2026-10-14 00:00:00`；字段存在后不回填或覆盖任何值。无数据库记录的历史手工目录列表 timestamp 为 NULL。

## 创建验证

### 本地数据集

- `GET /task/list_dataset` 返回 `{ips:[{ip_name}],tools:["CBMC","CPAchecker","KLEE"]}`。
- `POST /task/create_task` 正文 `{ip_name:"AttiCal",tool:"CBMC",userprompt:"可选要求"}`，返回 HTTP 201、`{task_id,timestamp,status:"queued"}`。tool 必填，userprompt 可省略、为空或 NULL；不接受手动 ID 和文件路径入口。

完整复制 `dataset/16-ip/ip/<ip_name>/` 及共享 `include/`，保存为 `input/ip/<ip_name>/` 和 `input/include/`，保留子目录、相对引用结构及原文件字节。复制完成后才排队执行，拒绝越界名称、符号链接和特殊文件；准备失败清理任务及映射。

### 远程项目

- `POST /project/create_project` 正文 `{projectID:"1001",source:"keti2",tool:"CBMC",userprompt:"可选要求"}`，返回 HTTP 202、`{projectID,keti,timestamp,status:"accepted"}`。source 可省略，默认 keti2，仅支持 keti2/keti3。课题三 projectID 必须是正整数的字符串。
- `GET /project/get_progress?projectID=...&source=keti2` 返回 `{projectID,keti,status,error?,total,finished,tasks:[{task_id,timestamp,ip_id,ip_name,status,...}],batches:[{timestamp,status,error?,total,finished,tasks}]}`。
- `GET /project/get_results?projectID=...&source=keti2` 返回 `{projectID,keti,tasks:[{task_id,timestamp,ip_id,status,files:[{path,size,kind,download_url}]}],batches:[{timestamp,tasks}]}`，只返回 workspace 内 output 目录的产物，不扫描进度接口中的文件。

查询 source 必填，返回该来源同项目所有批次。扁平 tasks 与总计数包含所有批次，batches 按 timestamp 升序排列；进度顶层 status/error 为最新批次状态，每批状态单独返回。重复提交不覆盖或删除任何旧任务，无项目删除入口。无对应项目返回 404，空白/非法参数返回 422。

后台先准备全部 IP，再逐个验证；单条准备失败不阻止其他 IP。单任务删除取消该任务，不取消整个项目，继续余下任务。进度按任务 verification_status 汇总，普通续聊状态不覆盖验证结论。项目状态支持 accepted、collecting、running、completed、failed、cancelled、empty。空项目或尚未形成数据库记录的失败项目只保存在内存，重启后不保留。

全部来源支持 CBMC、CPAchecker、KLEE；远程请求 tool 可省略，默认 CBMC，非法值返回 422。每次提交均将所选工具传入任务元数据及验证提示词。本地/课题二/课题三使用统一提示词构建，明确工具、输入、工作目录与完成报告要求；远程来源要求适配实际形式模型。可选用户提示词末尾以 `<userpropmt>\n用户内容\n</userpropmt>` 包裹；与默认说明冲突时以用户要求为准，不冲突时同时遵循。默认业务说明不混入用户段。

## 紧凑列表、详情与删除

`GET /task/list_tasks` 返回所有数据库任务及无数据库记录的旧手动任务目录。可选 `projectID`、`task_id`、`keti=keti2|keti3` 查询参数，精确匹配，多个条件取交集。

响应为 `{tasks:[{task_id,projectID,keti,timestamp,ip_id,ip_name,status,chatstatus,created_at?,missing_directory,directory_missing,data_missing}]}`。列表不返回提示词或扫描完整产物；status 为验证状态，chatstatus 为当前对话状态。无历史名称时 ip_name 为空字符串，不猜测补齐。

目录被手动移除时 status=missing、directory_missing/missing_directory=true，仍保留数据库记录；目录存在但元数据缺失、损坏、不可安全读取或 input/workspace/pi_session 目录缺失时 data_missing=true，不能令整个列表失败。NULL 记录保持原值，前端不要据此猜测来源。

`GET /task/get_task?task_id=...` 保留详情、历史提示词与 workspace 文件列表，新任务额外返回 ip_name/tool/timestamp。`DELETE /task/delete_task?task_id=...` 永久删除目录、会话及数据库记录，返回 `{task_id,status:"deleted"}`；缺目录但数据库仍有记录也可以显式删除。无目录且无映射时返回 404。删除先等待输入收集及验证/聊天退出，避免文件复制与目录删除竞争；损坏元数据不阻止删除。单任务删除不取消同批其他 IP 或其他批次。

## 下载

- `GET /task/get_file?task_id=...&path=...&download=true` 保留 workspace 单文件下载，path 相对 workspace，报告 HTML 预览仍使用沙箱头。
- `GET /task/download_task?task_id=...` 返回 ZIP 附件，顶层目录为 task_id，完整包含 input、files.csv、pi_session、task.json、workspace 及其他任务文件和空目录。拒绝任何符号链接及特殊文件，读取时使用目录文件描述符及不跟随链接的打开方式，避免泄漏任务之外的文件。压缩失败删除临时 ZIP，响应结束后清理临时文件。运行中的任务下载是即时快照，不保证并发写入内容的一致性。

## 课题二输入

默认查询 `http://8.130.30.48:8877/api/search/searchSoftwareIPByProjectId`，字符串参数 projectId，响应要求 code=0、result 列表，每项有 ipId。

仅收集 `ipMsg.entity.entityImplementation.dotC/dotH` 与 `ipMsg.formalModel.stateMachine/contracts/nonfunctionalConstraint/invariant` 的非空、非“无”文件来源。字段支持字符串或字符串列表，不当作正文。业务 ip_id 取 `ipMsg.entity.basicInformation.id`，名称取 name，仅存任务元数据。

优先显式路径映射与本机可读文件；HTTP(S) URL 用 GET，不可读的其他路径通过课题二 `POST /api/file/downloadFile` 获取，请求正文 `{filePath:"原始路径"}`，UTF-8 JSON。C/H 保持同目录，basename 重名加编号，files.csv 记录 ipId、原始 source、完整 field 和实际绝对 path；准备失败保留已收集清单。

## 课题三输入

`server/tmp_keti3.py` 是临时文件服务，只服务唯一 projectID 和 `tmp/NWM_synthesis.zip`。运行 `python3 server/tmp_keti3.py`，默认 127.0.0.1:50053。正式对接时修改业务配置地址。

课题三调用 `POST /api/verify`，正文 `{project_id:"1001"}`，随后 GET 响应 zip_url；不调用 synthesize，不自行拼接远端路径。下载完整 ZIP 保存为任务根目录 keti3.zip，全部产物视为一个 IP，解压到 input 保留路径和原编码，files.csv 记录 ZIP 和所有文件。拒绝路径穿越、符号链接、特殊文件、重复路径与覆盖；下载上限 256 MiB，解压上限 1 GiB，条目上限 10000。

IR 为形式模型，实际产物根层 .c/.h 为主代码，iplib 等子目录是依赖；包装目录由 agent 确定。GBK/gb18030 输入不改写，必要转换只在 workspace 中进行。产物未包含可用 IR 时必须报告规约缺失，不得声称已证明符合未提供的模型。

## 暂停与续聊

`POST /task/send_message` 正文 `{task_id,message}`，返回 HTTP 202、`{task_id,status}`。运行中消息作为后续补充，暂停/结束任务重新排队并加载本任务持久会话恢复上下文，不读取其他会话。输入准备期间拒绝对话。

`POST /task/pause_task` 正文 `{task_id}`，等待输出停止并释放 Pi 后返回 `{task_id,status:"paused"}`，排队任务也可以暂停。继续发送消息即可恢复；页面断开仅停止订阅，不暂停执行。

status/chatstatus 支持 queued、running、paused、idle、completed、failed、cancelled，verification_status 保存验证状态。idle 表示普通对话结束，completed 表示新生成有效报告；首次验证无有效报告判定 failed。

`GET /task/get_events?task_id=...` 重放历史并持续推送 NDJSON。用户事件 `{type:"user",message,turn_id,event_id}`，助手/工具事件 `{type:"agent",data,turn_id,event_id}`，状态事件 `{type:"status",status,turn_id,event_id}`；event_id 用于去重，turn_id 区分轮次。

## 配置与测试

业务地址在 `server/app/vip_task/config.py` 配置，修改后重启：KETI2_SEARCH_URL、KETI2_DOWNLOAD_URL（空字符串禁用路径下载）、KETI3_BASE_URL（默认 http://127.0.0.1:50053，不含 /api）。地址不读取环境变量。

环境变量：VIP_PROJECT_DB 默认项目根 projects.sqlite3；VIP_SOURCE_PATH_MAP 默认 `{}`，JSON 路径前缀到本机目录映射，最长前缀优先且拒绝越界；VIP_SOURCE_TIMEOUT 默认 30 秒；VIP_KETI3_TIMEOUT 默认 120 秒。

服务重启将未完成任务落盘 cancelled，不自动执行；正常关闭取消编排与任务、释放 Pi 并关闭 SQLite。写入映射失败回滚目录；回滚也失败时本进程保留临时批次归属供查询和按 task_id 删除，应在重启前处理。日志记录流程、状态和 HTTP 方法/路径/耗时，不记录请求正文、查询参数或提示词。

在 `server/` 执行 `uv run python -m unittest discover -s tests -v`。测试使用临时目录、临时 SQLite 和网络/Pi 替身，不操作真实任务或默认数据库，覆盖历史迁移及重启不覆盖新记录、同项目并发批次隔离、同批时间一致、来源隔离、ID 碰撞、本地复制、列表缺数据标识、删除续执行、ZIP 安全及暂停续聊。
