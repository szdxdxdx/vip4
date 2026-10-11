# 分析 CPAchecker 验证结果

## 输出目录

```
<suite>/
|   output/
|   |   cpachecker/
|   |   |   <case_name>/
|   |   |   |   cpachecker_stdout.txt
|   |   |   |   cpachecker_stderr.txt
|   |   |   |   cpachecker_output/
|   |   |   |   result.json
|   |   ai_agent/
|   |   report.html
|   |   report.json
```

读取 `result.json` 快速了解结论；需要进一步分析原因时，使用命令工具或自定义临时脚本过滤 CPAchecker 输出，常用命令包括：

```bash
# 查看最终验证结果
rg 'Verification result:' cpachecker_stdout.txt
# 查看停止原因、循环界和资源统计
rg 'Verification result:|Bound k:|Maximum loop iteration reached:|Time for analysis:|Memory used by analysis:' cpachecker_output/Statistics.txt
# 查看错误和重要警告
rg -i 'error|exception|warning|severe' cpachecker_stderr.txt cpachecker_stdout.txt
# 查找 CPAchecker 生成的反例、违规路径和 witness
find cpachecker_output -type f | rg -i 'counterexample|violation|witness|assignment'
```

`TRUE` 表示当前模型、配置和 specification 下未发现可达违规状态，`FALSE` 表示找到可达违规路径，`UNKNOWN` 表示当前分析无法证明或反证。必须结合入口函数、specification、循环展开充分性、warning 和建模范围审查结果，不能只读取最终一行，也不能把聚合的 case 结论改写成逐条断言 SUCCESS/FAILURE。

FALSE 时优先查看 CPAchecker 生成的 counterexample、assignment、violation witness，提取失败断言位置、关键变量赋值和路径。每个明确报告的不通过断言都必须在最终 HTML 中关联一条精简反例路径；若工具未生成或脚本无法提取，必须明确标记反例路径缺失，不得编造。UNKNOWN 分析中生成的 candidate counterexample 可能不可行，不得作为已确认反例写入结论或报告；只有最终 `Verification result: FALSE` 的 case 才能发布精简反例。

分别审查 specification 警告和普通 soundness warning。断言函数已被 specification 监视时，某个分析 CPA 仍可能报告未知调用或忽略副作用；这不等同于 specification 失配，但必须结合配置和路径说明对可信度的影响。
