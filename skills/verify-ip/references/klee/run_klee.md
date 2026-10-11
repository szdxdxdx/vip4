# 执行 KLEE 验证

## 创建验证配置

KLEE 的验证配置 `<case_name>.json` 示例如下：
```json
{
  "splited_from": <null|str>,
  "reduced_from": <null|str>,
  "compile": {
    "clang": "clang",
    "files": [<str>],
    "options": {
      "-I": [...],
      "-D": [...],
      "-g": true,
      "-emit-llvm": true,
      "-c": true,
      "-o": <str>
    }
  },
  "klee": {
    "executable": "klee",
    "bc_file": <str>,
    "entry_point": <str>,
    "options": {
      "--watchdog": true,
      "--emit-all-errors": true,
      "--max-time": <str>,
      "--output-dir": <str>
    }
  },
  "py_subprocess": {
    "timeout": <int>
  }
}
```

字段说明：
- `compile.clang` clang 可执行文件路径
- `compile.files` 填写所有参与编译的 C 文件路径
    包含 IP 源文件（直接使用原始文件路径或 patched 版本）、依赖文件或桩文件，以及验证驱动 `<case_name>.c`，只填写最小必要集合，路径使用绝对路径
- `compile.options` 填写 clang 支持的参数
    开放结构，任何 clang 支持的参数都可以直接加进去
    string / number 以 key-val 形式加入命令，例如 `"-o": "/abs/tmp/case.bc"` 转换为 `-o /abs/tmp/case.bc` 两个独立的 argv
    array 以 key-val 形式展开每项加入命令，例如 `"-I": ["a/", "b/"]` 转换为 `-I a/ -I b/`
    bool true 以 flag 形式加入命令，例如 `"-g": true` 转换为 `-g`
    bool false 和未指出的配置项不加入命令
- `compile.options.-I` 填写头文件搜索路径，必须包含待验证 IP 的公共头文件目录和 IP 实现文件所在目录
- `compile.options.-D` 填写预处理器宏定义，必须通过 `-D` 添加 `__GCC_COMPILED__`（原代码中 `std_basal.h` 依赖此宏区分 GCC 与 MSVC 的 64 位整数类型）
- 必须填入 `-g`、`-emit-llvm` 和 `-c` 三个选项，生成带调试信息的 LLVM bitcode 目标文件，并通过 `-o` 指定 bitcode 输出路径，建议保存在 `<verify_ip_workspace>/tmp/` 目录下
- `klee` KLEE 配置项，最终转换为命令 `klee [options] bc_file --entry-point=entry_point`
- `klee.executable` KLEE 可执行文件路径
- `klee.bc_file` 填写 compile 步骤生成的 LLVM bitcode 文件路径（绝对路径）
- `klee.entry_point` 填写验证入口函数名，即验证驱动中的 case 函数名
- `klee.options` 填写 KLEE 支持的参数，
    开放结构，参数转换规则与 `compile.options` 相同
    `--entry-point` 已在 `klee.entry_point` 字段中单独指定，不应重复出现在 `klee.options` 中
    `--output-dir` 指定 KLEE 输出目录，建议统一为 `<suite>/output/klee/<case_name>/klee-out`

---

若无明确要求，默认启用以下 KLEE 配置项（功能性验证）：
- `--watchdog` 监控执行时间，配合 `--max-time` 使用
- `--emit-all-errors` 即使发现错误也继续探索其他路径
- `--max-time` 设置 KLEE 内部最大执行时间，建议比 `py_subprocess.timeout` 小 60 秒，使 KLEE 正常退出而非被超时杀死

执行非功能性验证时，额外启用以下 KLEE 配置项：
- `--check-div-zero` 检测除零错误
- `--check-overshift` 检测移位溢出

---

Snap KLEE 头文件位于 `/snap/klee/current/usr/local/include`，需加入 -I
配置指定的 bitcode 输出目录必须预先创建

## 执行验证

使用 `<skill>/scripts/klee/run_klee.py` 执行验证
脚本将简要打印 KLEE 执行结果，完整结果将保存（覆盖写入）到 `<suite>/output/klee/<case_name>/` 目录：
- `compile_stdout.txt` clang 编译 stdout
- `compile_stderr.txt` clang 编译 stderr
- `klee_stdout.txt` KLEE stdout
- `klee_stderr.txt` KLEE stderr
- `klee-out/` KLEE 输出目录
- `result.json`

## 验证策略调整指南

若 KLEE 因路径爆炸导致超时或内存耗尽，可尝试以下策略：
1. 增大 `--max-time` 和 `py_subprocess.timeout`，给予更多探索时间
2. 缩减符号化范围，将部分符号量改为具体值，减少路径分支
3. 拆分 case，将复杂的合取式拆分为多个独立的 sub-case 分别验证
4. 使用 `--max-instructions` 限制 KLEE 探索的指令数上限
5. 使用 `--max-depth` 限制 KLEE 探索的路径深度

以上策略需在最终报告中注明。

## 验证策略调整指导和错误处理

### 浮点处理

KLEE 对浮点符号化的支持极其有限，不应尝试对浮点输入进行全符号化。
参见 `<skill>/references/klee/make_driver.md` 中浮点数一节的处理策略。
