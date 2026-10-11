# 分析 CBMC 验证结果

## 输出目录

```
<suite>/
|   output/
|   |   cbmc/
|   |   |   <case_name>/
|   |   |   |   cbmc_stdout.json 
|   |   |   |   cbmc_stderr.txt
|   |   |   |   result.json
|   |   ai_agent/
|   |   report.html
|   |   report.json
```

读取 `<case_name>/result.json` 快速了解结论；

需要进一步分析原因时，使用 jq、grep 等工具或自定义临时脚本过滤查看 CBMC 原始输出，常用命令包括：

```bash
# 查看总体验证状态（success / failure）
jq '.[] | select(.cProverStatus) | .cProverStatus' cbmc_stdout.json
# 统计断言通过/失败数量
jq '[.[] | select(.result) | .result[] | .status] | {total: length, pass: map(select(.=="SUCCESS")) | length, fail: map(select(.=="FAILURE")) | length}' cbmc_stdout.json
# 列出所有断言（property、描述、结果）
jq '[.[] | select(.result) | .result[] | {property, description, status}]' cbmc_stdout.json
# 仅列出失败断言
jq '.[] | select(.result) | .result[] | select(.status=="FAILURE") | {property, description}' cbmc_stdout.json
# 查看失败断言的反例路径（关键变量赋值，跳过隐藏步骤）
jq '.[] | select(.result) | .result[] | select(.status=="FAILURE") | .trace[] | select(.stepType=="assignment" and .hidden==false) | {lhs, value: .value.data, type: .value.type, file: .sourceLocation.file, line: .sourceLocation.line}' cbmc_stdout.json
```
若验证超时，CBMC 原始输出的 JSON 内容将不完整，jq 无法解析。
