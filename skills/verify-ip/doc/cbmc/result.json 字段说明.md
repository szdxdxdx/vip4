
```jsonc
{
  // CBMC 验证结论
  // - SUCCESS 表示 CBMC 验证通过
  // - FAILURE 表示 CBMC 验证不通过，断言失败
  // - TIMEOUT 表示 CBMC 验证超时，未得出结论
  "conclusion": "SUCCESS | FAILURE | TIMEOUT",

  // CBMC 的退出码，若超时则为 null
  "return_code": <null|int>,

  "timing": {
    // CBMC 执行用时，单位为秒
    "duration": <int>,
    // 是否超时
    "timed_out": <bool>
  },

  // CBMC 断言统计，若超时则为 null
  "assertions": null | {
    "total":  <int>,
    "passed": <int>,
    "failed": <int>
  }
}
```
