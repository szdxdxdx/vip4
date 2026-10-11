```jsonc
{
  // 待验证 IP 的名称
  "ip": <str>,

  // AI Agent 给出的整体验证结论
  "ai_agent_conclusion": {
    "functional": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS",
    "nonfunctional": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
  },

  "timing": {
    // 验证套件的创建时间
    "suite_created_at": "YYYY-MM-DD HH:MM:SS",
    // 验证报告的生成时间
    "report_generated_at": "YYYY-MM-DD HH:MM:SS",
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
      { "original": <str>, "splited": [ <str>, ... ] }
    ]
  },

  // 每个 case 的验证结果
  "cases": {
    "<case_name>": {
      // 若当前 case 是拆分得到的 sub-case，填写其原 case 名；否则为 null
      "splited_from": <null|str>,
      // 若当前 case 是缩减验证范围得到的 reduced-case，填写其原 case 名；否则为 null
      "reduced_from": <null|str>,

      // case 级结论
      "conclusion": {
        // KLEE 的验证结论，提取自 case 的 reult.json
        "klee": "COMPLETED | ERRORS | TIMEOUT | INCOMPLETE",
        // AI Agent 综合判断结论
        "ai_agent": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
      },

      "timing": {
        // KLEE 执行耗时，单位为秒
        "duration": <int>,
        // 是否超时
        "timed_out": <bool>
      },

      // KLEE 执行统计（验证超时则为 null；结构同 result.json.statistics，
      // 含 coverage、termination_reasons、external_calls）
      "statistics": null | {
        "explored_paths": <int>,
        "completed_paths": <int>,
        "generated_tests": <int>,
        "total_instructions": <int>,
        "coverage": null | {
          "covered_instructions": <int>,
          "uncovered_instructions": <int>,
          "percentage": null | <float>
        },
        "termination_reasons": null | {
          "exit": <int>,
          "early": <int>,
          "solver_error": <int>,
          "program_error": <int>,
          "user_error": <int>,
          "execution_error": <int>,
          "early_algorithm": <int>,
          "early_user": <int>
        },
        "external_calls": null | <int>
      },

      // KLEE 警告信息（来自 result.json；结构同 result.json.warnings）
      "warnings": null | {
        "total": <int>,
        "concretizing": <int>,
        "items": [
          {
            "type": <str>,
            "message": <str>
          }
        ]
      },

      // 错误摘要（无错误或超时则为 null）
      "error_summary": null | {
        "total": <int>,
        "by_type": {
          "ptr": <int>,
          "assert": <int>,
          "div": <int>,
          "overflow": <int>,
          "external": <int>,
          "user": <int>,
          "free": <int>,
          "other": <int>
        }
      },
    }
  },

  // 全部 case 的 KLEE 统计汇总
  "statistics": {
    // 总探索路径数
    "total_explored_paths": <int>,
    // 总生成测试用例数
    "total_generated_tests": <int>,
    // 总错误数
    "total_errors": <int>
  }
}
```