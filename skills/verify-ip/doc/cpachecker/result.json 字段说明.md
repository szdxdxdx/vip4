```jsonc
{
  // CPAchecker 验证结论，直接使用工具输出中的 Verification result
  // - TRUE: CPAchecker 认为目标性质成立，未发现可达违规。
  // - FALSE: CPAchecker 找到可达违规。
  // - UNKNOWN: CPAchecker 正常运行但不能给出确定结论。
  // - TIMEOUT: 超时(由 py 脚本补充)
  // - null：没有解析到最终结果，通常要结合 tool_error 和 error_summary。
  "conclusion": null | "TRUE | FALSE | UNKNOWN | TIMEOUT",

  // CPAchecker 执行的退出码；若超时则为 null
  "return_code": <null|int>,

  "timing": {
    // CPAchecker 执行用时，单位为秒
    "duration": <int>,
    // 是否超时
    "timed_out": <bool>
  },

  "verification_goal": {
    // 根据 case 配置推断的验证目标类别
    "kind": "assertion-reachability | memory-safety | integer-overflow | specification-reachability",
    // 对 CPAchecker 原始结果的稳定解释代码，供报告展示使用
    "interpretation": "NO_REACHABLE_VIOLATION | REACHABLE_VIOLATION | NO_FINAL_CONCLUSION | TIME_LIMIT_REACHED | TOOL_ERROR"
  },

  // CPAchecker 启动或执行是否发生工具层错误
  "tool_error": <bool>,
  // 工具错误摘要；无工具错误时为空字符串
  "error_summary": <str>,

  "assertions": {
    // 从 case 驱动 C 文件中提取到的 assert(...) 数量
    "source_count": <int>,
    // specification 监控是否报告失配
    "monitoring": "NO_MISMATCH_REPORTED | MISMATCH_REPORTED | UNKNOWN",
    // CPAchecker 明确报告的违规数量
    "confirmed_violation_count": <int>,
    // CPAchecker 明确报告的违规点
    "confirmed_violations": [
      {
        "id": <str>,
        "kind": <str>,
        "file": <null|str>,
        "line": <null|int>,
        "expression": <str>
      }
    ]
  },

  // 从 cpachecker_output/Statistics.txt 提取的核心统计字段
  "statistics": {
    "Bound k": <int|float>,
    "Maximum loop iteration reached": <int|float>,
    "Function coverage": <int|float>,
    "Visited lines": <int|float>,
    "Total lines": <int|float>,
    "Line coverage": <int|float>,
    "Visited conditions": <int|float>,
    "Total conditions": <int|float>,
    "Condition coverage": <int|float>,
    "Number of target states": <int|float>,
    "Time for Analysis": <int|float>,
    "CPU time for analysis": <int|float>,
    "Total time for CPAchecker": <int|float>,
    "Total CPU time for CPAchecker": <int|float>
  },

  "counterexamples": {
    // 解析到的文本反例数量，来源为 cpachecker_output/Counterexample.*.txt
    "available": <int>,
    // 成功关联到 confirmed_violations 中某个 violation_id 的反例数量
    "mapped": <int>
  },

  "warnings": {
    "specification": {
      // specification 监视相关警告数量；非 0 时本次结果通常需要判为不可信或至少人工复核
      "count": <int>
    },
    // soundness 相关警告按类别归并后的摘要
    "soundness": [
      {
        "category": "UNKNOWN_FUNCTION | OVERAPPROXIMATION | IGNORED_SIDE_EFFECTS | OTHER_SOUNDNESS_RISK",
        "subject": <null|str>,
        "count": <int>
      }
    ]
  }
}
```
