# 生成 KLEE 报告

报告脚本读取套件中的每个 case 结果和 `output/ai_agent/` 下的分析文件：

```bash
<skill>/.venv/bin/python <skill>/scripts/klee/make_report.py --suite <verify_ip_workspace>/klee_suite
```

报告阶段不需要额外转换脚本：`run_klee.py` 生成的 `output/klee/<case>/result.json` 和 `klee-out` 是工具数据入口；Agent 读取这些内容后，将每个 case 的分析写入 `output/ai_agent/<case>.md`，并写入 `output/ai_agent/conclusion.json`。可选地写入 `issues.md`、`conclusion.md` 和 `experience.md`。完成这些文件后再执行报告脚本。

`conclusion.json` 的最小格式：

```json
{
  "overall": {"functional": "PASS", "nonfunctional": "INCONCLUSIVE"},
  "cases": {"case_1": "PASS"}
}
```

报告脚本会直接读取 KLEE 的 case 结果和上述 Agent 分析；缺少可选 Markdown 文件时仍会生成报告，缺少 case 结论时记为 `INCONCLUSIVE`。

