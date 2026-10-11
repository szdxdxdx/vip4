```jsonc
{
  // KLEE 验证结论
  // - COMPLETED：正常完成所有路径探索，未发现错误
  // - ERRORS：完成所有路径探索，但发现错误（存在 .err 文件）
  // - TIMEOUT：超时中断，未完成全部探索
  // - INCOMPLETE：未正常完成（编译失败、异常崩溃、输出不完整等）
  "conclusion": "COMPLETED | ERRORS | TIMEOUT | INCOMPLETE",

  // KLEE 退出码，若超时则为 null
  "return_code": <null|int>,

  "timing": {
    // KLEE 执行用时，单位为秒
    "duration": <int>,
    // 是否超时
    "timed_out": <bool>
  },

  // KLEE 执行统计；若超时或输出不完整则为 null
  "statistics": null | {
    // 探索的路径数
    "explored_paths": <int>,
    // 完成的路径数
    "completed_paths": <int>,
    // 生成的测试用例数（.ktest 文件数量）
    "generated_tests": <int>,
    // 执行的指令总数
    "total_instructions": <int>,

    // 指令覆盖率（run.stats 提取）；无法读取 run.stats 时为 null
    "coverage": null | {
      // 已覆盖指令数
      "covered_instructions": <int>,
      // 未覆盖指令数
      "uncovered_instructions": <int>,
      // 覆盖率百分比 covered / (covered+uncovered)，保留一位小数；无覆盖统计时为 null
      "percentage": null | <float>
    },

    // 路径终止原因分布（run.stats 提取）；无法读取时为 null
    "termination_reasons": null | {
      // 正常退出
      "exit": <int>,
      // 提前终止
      "early": <int>,
      // 求解器错误
      "solver_error": <int>,
      // 程序错误
      "program_error": <int>,
      // 用户错误
      "user_error": <int>,
      // 执行错误
      "execution_error": <int>,
      // 算法提前终止
      "early_algorithm": <int>,
      // 用户提前终止
      "early_user": <int>
    },

    // 外部函数调用次数（run.stats 提取）；无法读取时为 null
    "external_calls": null | <int>
  },

  // KLEE 警告信息（warnings.txt 提取）；无警告或无法读取时为 null
  "warnings": null | {
    // 警告总数（按 "KLEE: WARNING" 条目切分）
    "total": <int>,
    // 具体化警告数量（silently concretizing）
    "concretizing": <int>,
    // 警告原文列表
    "items": [
      {
        // 警告类型：concretizing | external | other
        "type": <str>,
        // 警告原文（可能跨行）
        "message": <str>
      }
    ]
  },

  // 错误摘要，按类型分组；无错误则为 null
  "error_summary": null | {
    // 错误总数
    "total": <int>,
    // 按错误类型统计
    "by_type": {
      // 指针错误（.ptr.err）
      "ptr": <int>,
      // 断言失败（.assert.err）
      "assert": <int>,
      // 除零错误（.div.err）
      "div": <int>,
      // 溢出（.overflow.err）
      "overflow": <int>,
      // 外部函数调用失败（.external.err）
      "external": <int>,
      // 用户错误（.user.err，不可满足的 assume）
      "user": <int>,
      // 非法释放（.free.err）
      "free": <int>,
      // 其他错误类型
      "other": <int>
    }
  }
}
```