# 执行 CBMC 验证

## 创建验证配置

CBMC 的验证配置 `<case_name>.json` 示例如下：
```json
{
  "splited_from": <null|str>,
  "reduced_from": <null|str>,
  "py_subprocess": {
    "timeout": <int>
  },
  "cbmc": {
    "executable": "cbmc",
    "files": [<str>],
    "options": {
      "-I": [...],
      "-D": [...],
      "--unwind": ...,
      "--depth": ...,
      "--function": ...,
      "--trace": true,
      "--json-ui": true,
      "--unwinding-assertions": true,
      ...
    }
  }
}
```

字段说明：
- `cbmc` CBMC 配置项，最终转换为命令 `cbmc [options] files...`
- `cbmc.files` 填写所有参与验证的 C 文件路径
    包含 IP 源文件（直接使用原始文件路径）、依赖实现文件或桩文件，以及验证驱动 `<case_name>.c`，只填写最小必要集合
- `cbmc.options` 填写 CBMC 支持的参数
    开放结构，任何 CBMC 支持的参数都可以直接加进去
    string / number 以 key-val 形式加入命令，例如 `"--unwind": 15` 转换为 `--unwind 15` 两个独立的 argv
    array 以 key-val 形式展开每项加入命令，例如 `"-I": ["a/", "b/", "c/"]` 转换为 `-I a/ -I b/ -I c/`
    bool true 以 flag 形式加入命令，例如 `"--json-ui": true` 转换为 `--json-ui`
    bool false 和未指出的配置项不加入命令
- `cbmc.options.-I` 填写头文件搜索路径
- `cbmc.options.--function` 填写验证入口函数，即验证驱动中的 case 函数名
- `cbmc.options.--unwind` 填写循环展开次数上限
    若无循环，初值设为 1
    若有循环，初值设为 max(所有循环显式上界) + 5，考虑嵌套循环，应覆盖最长路径
    （含驱动代码自身引入的循环和 IP 实现中的循环）
    若无显式上界，则初值设为 15

---

若无明确要求，默认启用以下 CBMC 配置项
- `--trace`
- `--json-ui`
- `--unwinding-assertions`

执行功能性验证时，通常启用以下 CBMC 配置项
不要让非功能性检查的断言干扰功能性验证的结论，导致误判
- `--no-bounds-check`
- `--no-pointer-check`
- `--no-div-by-zero-check`
- `--no-signed-overflow-check`
- `--no-undefined-shift-check`
- `--no-pointer-primitive-check`

执行非功能性验证时，通常启用以下 CBMC 配置项
- `--bounds-check`
- `--pointer-check`
- `--div-by-zero-check`
- `--signed-overflow-check`
- `--undefined-shift-check`
- `--pointer-overflow-check`
- `--enum-range-check`
- `--pointer-primitive-check`

执行非功能性验证时，以下 CBMC 配置项视项目情况开启
- `--unsigned-overflow-check`
- `--float-div-by-zero-check`
- `--float-overflow-check`
- `--nan-check`
- `--memory-leak-check`
- `--memory-cleanup-check`

## 执行验证

使用 `<skill>/scripts/cbmc/run_cbmc.py` 执行验证
脚本将简要打印 CBMC 执行结果，完整结果将保存（覆盖写入）到 `<suite>/output/cbmc/<case_name>/` 目录：
- `cbmc_stdout.json` CBMC stdout
- `cbmc_stderr.txt`  CBMC stderr
- `result.json`

## 验证策略调整规则

若 case 验证超时或无法得出结论，可尝试调整验证策略（拆分 case 或缩减验证范围），尽可能使所有 case 得出有效结论。
若超时，可放大 `timeout`、调整 CBMC 配置、拆分 case 或缩减验证范围

## 验证策略调整指导和错误处理

### 浮点 SAT

若因大量浮点符号化运算导致 SAT 求解超时，
可将参与大量浮点运算的配置参数固定为典型值，而非用 `nondet_float()` 全符号化，
或改用代表性单下标代替符号化下标，或拆分约束，减小验证范围。
使用 `--smt2` 作为备选后端。

以上策略需在最终报告中注明：验证结论仅在所选参数范围/下标范围内成立，不等价于完整数学规格
