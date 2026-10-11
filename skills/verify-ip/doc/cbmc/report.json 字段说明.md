```jsonc
{
  // IP 的名称
  "ip": <str>,

  // AI Agent 给出的整体验证结论
  "ai_agent_conclusion": {
    "functional":    "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS",
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
      { "original": <str>, "splited": [ <str> ] }
    ]
  },

  // 各 case 的验证结论
  "cases": {
    "<case_name>": {

      "conclusion": {
        // CBMC 的验证结论，提取自 case 的 result.json
        "cbmc": "SUCCESS | FAILURE | TIMEOUT",
        // AI Agent 给出的结论
        "ai_agent": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
      },

      // 以下内容来自 case 的 config.json
      "splited_from": <null|str>,
      "reduced_from": <null|str>,

      // 以下内容来自 case 的 result.json
      "assertions": null | {
        "total": <int>,
        "passed": <int>,
        "failed": <int>
      },
      "timing": {
        "duration": <int>,
        "timed_out": <bool>
      }
    }
  },

  // 全部 case 的断言统计
  // 仅统计已明确的出结论的断言，忽略验证超时或未得出结论的 case（因为这些 case 无法统计断言）
  "assertions": {
    "total": <int>,
    "passed": <int>,
    "failed": <int>
  }
}
```
