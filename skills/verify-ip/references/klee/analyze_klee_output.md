# 分析 KLEE 验证结果

## 输出目录

```
<suite>/
|   output/
|   |   klee/
|   |   |   <case_name>/
|   |   |   |   result.json
|   |   |   |   klee-out/
|   |   |   |   |   info
|   |   |   |   |   messages.txt
|   |   |   |   |   warnings.txt
|   |   |   |   |   test*.err
|   |   |   |   |   test*.ktest
|   |   |   |   |   test*.kquery
|   |   |   |   |   assembly.ll
|   |   |   |   |   run.stats
|   |   |   |   klee_stdout.txt
|   |   |   |   klee_stderr.txt
|   |   ai_agent/
|   |   report.html
|   |   report.json
```

先读取 `<case_name>/result.json` 快速了解结论、统计和错误摘要。

需要进一步分析错误原因时，根据错误类型查看对应的 `.err` 文件。每种 `.err` 后缀对应一种错误类型（`.ptr.err` 指针错误、`.assert.err` 断言失败、`.div.err` 除零、`.overflow.err` 溢出、`.external.err` 外部函数调用失败、`.user.err` 不可满足的 assume、`.free.err` 非法释放），常用命令：

```bash
# 查看所有错误类型和数量
find <case-output>/klee-out -name '*.err' -printf '%f\n' | sort
# 查看单个错误详情（错误类型、文件、行号、调用栈、地址信息）
cat <case-output>/klee-out/test000001.ptr.err
# 查看所有错误详情
find <case-output>/klee-out -name '*.err' -exec cat {} \;
# 查看 KLEE 运行日志（含警告、具体化信息）
cat <case-output>/klee-out/messages.txt
# 查看 KLEE 警告信息
cat <case-output>/klee-out/warnings.txt
# 查看 KLEE 执行统计（探索路径数、测试用例数、指令数等）
grep 'KLEE: done:' <case-output>/klee-out/info
# 查看 KLEE 标准错误输出
cat <case-output>/klee_stderr.txt
# 查看 .ktest 测试用例内容（反例或代表性输入）
klee-ktest-tool <case-output>/klee-out/test000001.ktest
```

## 判定规则

- `FAILURE`：存在非 `user.err` 的 `.err` 文件；优先依据错误类型（`ptr`、`assert`、`div`、`overflow`、`external`、`free`）及其 `Error`、`File`、`Line`、`Stack` 内容判断。
- `SUCCESS`：工具正常结束，没有非 `user.err` 的错误文件，且 `info` 文件中包含完整的 `KLEE: done:` 统计信息。它表示已探索的输入空间内未发现错误，不自动等同于整个规约域。
- `TIMEOUT`：达到脚本超时限制；`result.json` 中 `timing.timed_out` 为 `true`，`statistics` 可能不完整。
- `INCONCLUSIVE`：编译失败、工具启动失败、输出不完整、退出码异常，或 `info` 文件中缺少必要的统计信息。

## 注意事项

- `user.err` 表示不可满足的 `klee_assume` 约束，属于建模问题而非 IP 实现错误，不应计入 functional 失败。
- `info` 文件中的 `KLEE: done:` 统计用于评估探索规模：`explored paths` 表示路径数量，`generated tests` 表示测试用例数量，`completed paths` 表示完整探索的路径数。
- `run.stats` 是 SQLite 格式的详细统计，通常不需要直接查看。
- `.ktest` 文件是反例或代表性测试输入，可使用 `klee-ktest-tool` 查看具体赋值。
- 完整错误原文、KLEE 日志信息和标准错误应当放在报告的 `details` 折叠框中；正文只保留摘要、工具结论和 Agent 结论。