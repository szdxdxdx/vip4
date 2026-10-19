# 课题五联调

真实服务地址未定，通过环境变量配置后重启后端：

- `KETI5_CALLBACK_URL`：进度回调完整地址。
- `KETI5_UPLOAD_URL`：报告上传完整地址。
- `KETI5_JENKINS_USER`：回调认证用户名。
- `KETI5_JENKINS_API_TOKEN`：回调认证令牌。
- `KETI5_TIMEOUT`：请求超时秒数，默认 30。

上传接口不复用 Jenkins 凭据。未配置地址时请求失败，不影响验证；上传按钮允许再次尝试。参数只属于本次任务，后续提交不覆盖旧任务。进度只发送 98 和 100，暂停不视为结束，失败和取消视为结束。上传采用完整任务目录的安全 ZIP，拒绝符号链接及特殊文件，成功或失败均清理临时 ZIP。仅保留最近一次上传失败状态。

## 伪后端

在 `/app/vip4/server` 执行：

```bash
uv run python tmp_keti5/tmp_keti5.py
```

伪后端仅监听本机，默认端口 50055，可用 `KETI5_MOCK_PORT` 修改。它校验 ZIP 并打印文件列表，不保存压缩包，不校验认证。

为 vip4 后端设置：

```bash
export KETI5_CALLBACK_URL=http://127.0.0.1:50055/demo-callback/notify
export KETI5_UPLOAD_URL=http://127.0.0.1:50055/sw/idep/plugin/reportUpload
```

前端示例参数：

```text
?projectId=1001&jobName=demo&buildId=3&toolName=CBMC&executionId=9e174276-fb22-4625-bb0f-17e4ea971415
```

五个参数缺一则整体忽略。本地数据集不保存参数，也不支持上传。buildId 落盘为字符串，回调时编码为精确 JSON 整数；上传表单保持字符串。

隔离测试不调用真实 Agent 或修改现有任务：

```bash
uv run python -m unittest discover -s tests -v
```
