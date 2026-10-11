```jsonc
{
  // IP 的名称
  "ip": <str>,

  // AI Agent 给出的整体验证结论；
  "ai_agent_conclusion": {
    "functional": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS",
    "nonfunctional": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
  },

  "timing": {
    // 验证套件的创建时间
    "suite_created_at": "YYYY-MM-DD HH:MM:SS",
    // 验证报告的生成时间
    "report_generated_at": "YYYY-MM-DD HH:MM:SS"
  },
  // 验证策略调整（各 case 间的关系）
  "strategy": {
    "original_cases": [
      // 原 case 名称
      <str>
    ],
    "reduced_cases": [
      // 原 case 和缩减后的 reduced-case 名称
      { "original": <str>, "reduced": <str> }
    ],
    "splited_cases": [
      // 原 case 和拆分后的 sub-case 名称
      { "original": <str>, "splited": [<str>] }
    ]
  },

  // 每个 case 的验证结果
  "cases": {
    "<case_name>": {
      // 若当前 case 是拆分得到的 sub-case，填写其原 case 名；否则为 null。
      "splited_from": null | <str>,
      // 若当前 case 是缩减验证范围得到的 reduced-case，填写其原 case 名；否则为 null。
      "reduced_from": null | <str>,

      // case 级结论。cpachecker 字段直接使用 CPAchecker 输出中的 Verification result
      // 仅当 Python 层超时控制触发时由脚本补充 TIMEOUT。
      "conclusion": {
        "cpachecker": "TRUE | FALSE | UNKNOWN | TIMEOUT",
        "ai_agent": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
      },

      "verification": {
        // CPAchecker 原始 Verification result；超时或工具未给出最终结果时为 null。
        "result": null | "TRUE | FALSE | UNKNOWN",
        "kind": "assertion-reachability | memory-safety | integer-overflow | specification-reachability",
        "interpretation": "NO_REACHABLE_VIOLATION | REACHABLE_VIOLATION | NO_FINAL_CONCLUSION | TIME_LIMIT_REACHED | TOOL_ERROR"
      },

      "scope": {
        "configuration": null | <str>,
        "specification": null | <str>,
        "entry_function": null | <str>,
        "source_assertions": <int>,
        "loop_bound": null | <str>,
        "maximum_loop_iteration_reached": null | <int|float>
      },

      "violations": {
        "confirmed": <int>,
        "extracted_trace_count": <int>,
        "counterexamples_available": <int>,
        "counterexamples_missing": <int>
      },

      "trust": {
        "status": "CLEAR | REVIEW | INVALID",
        "specification_warning_count": <int>,
        "soundness_warning_count": <int>,
        "soundness_categories": <int>
      },

      "execution": {
        "duration": <int>,
        "timed_out": <bool>,
        "tool_error": <bool>
      },

      "error_summary": <str>
    }
  },

  "statistics": {
    // 全部 case 的 CPAchecker 原始结果分布，含原 case、sub-case 和 reduced-case
    "cases": {
      "total": <int>,
      "true": <int>,
      "false": <int>,
      "unknown": <int>,
      "timeout": <int>,
      "tool_error": <int>,
      "conclusive": <int>,
      "conclusive_rate": <float>,
      "original": <int>,
      "sub_cases": <int>,
      "reduced_cases": <int>
    },
    // 功能性 case 的 CPAchecker 原始结果分布
    "functional": { <同 cases 结构的统计字段> },
    // 非功能性 case 的 CPAchecker 原始结果分布
    "nonfunctional": { <同 cases 结构的统计字段> },
    "violations": {
      "violating_cases": <int>,
      "confirmed_occurrences": <int>,
      "missing_counterexamples": <int>
    },
    "trust": {
      "specification_warning_cases": <int>,
      "soundness_warning_cases": <int>,
      "tool_error_cases": <int>
    },
    "execution": {
      "total_duration": <float>,
      "maximum_case_duration": <float>
    }
  }
}
```
