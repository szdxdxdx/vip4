# 软件 IP 验证工作流

使用指定的验证工具对待验证 IP 进行形式化验证，生成最终验证报告。

不同工具的验证工作流整体流程类似，主要包括：
- 构建验证套件
- 拆解验证 case，编写 case 驱动代码以及配置文件
- 执行 case 验证，分析验证结果，必要时动态调整验证策略
- 给出最终验证结论，生成验证结果报告

## 两类验证

所有验证工作流都包含两类验证：
- 功能性验证：验证 IP 实现是否满足形式规约描述的行为（前后置断言）
- 非功能性验证：检查数组越界、指针越界、整数溢出等与业务逻辑无关的编程语言层面问题

## 验证 case

功能性和非功能性需求将被拆分出多个小的验证 case 来单独验证。`<case_name>` 表示 case 的名字。
每个 case 都包含一份驱动文件 `<case_name>.c` 和一份配置文件 `<case_name>.json`，
驱动文件中包含了该 case 的前后置断言代码，配置文件中包含了 case 的信息以及验证工具的配置参数。
验证过程中，若某个 case 验证超时或无法得出结论，可尝试拆分 case 或缩减验证范围，生成新的 sub-case 或 reduced-case 来继续验证。
更多细节参见 `<skill>/references/ip/case.md`

## 工作目录结构

```
<verify_ip_workspace>/    # 本次 IP 验证的工作目录，由用户指定
|   tmp/                  # 存放临时文件
|   ir/                   # 存放 IR 文件的目录
|   <suite>/              # 验证套件，IP 验证的工作目录
|   |   suite.json        # 记录验证套件的基本信息
|   |   patched/          # 存放 IP 原始文件的修正版本
|   |   cases_tmpl.c      # 验证驱动模板，记录了所有待验证的性质
|   |   helper.c (.h)     # 验证辅助函数
|   |   <case_name>.c     # 验证驱动
|   |   <case_name>.json  # 验证配置，与验证驱动一一对应
|   |   output/
|   |   |   <tool_name>/         # 验证工具输出
|   |   |   |   <case_name>/
|   |   |   |   |   result.json  # SKILL 内部脚本对工具输出内容的简要分析
|   |   |   |   |   ...          # 其他输出内容因工具而异
|   |   |   ai_agent/            # 由 AI Agent 给出的验证结论评价
|   |   |   |   <case_name>.md   # case 补充分析，可选
|   |   |   |   conclusion.json  # 验证结论
|   |   |   |   conclusion.md    # 验证结论
|   |   |   |   issues.md        # 验证过程中遇到的问题与处理，可选
|   |   |   |   experience.md    # 验证经验总结
|   |   |   report.html   # 最终验证报告
|   |   |   report.json   # 最终验证报告
```

- `<tool_name>` 表示验证工具的名称，可选值： `cbmc | cpachecker | klee`
- `<suite>/` 表示验证套件目录，可选值： `<cbmc_suite> | <cpachecker_suite> | <klee_suite>`

SKILL 执行过程中产生的任何临时文件，都统一放在 `<verify_ip_workspace>/tmp/`，包括但不限于：
任何临时脚本、调试副本和中间结果、任何 SKILL 文档未明确提及的文件或产物

## 工作流步骤

### step-1 创建验证套件

使用 `<skill>/scripts/<tool_name>/build_suite.py` 生成验证套件
脚本参数：
- `--ir    <dir>` 指定 IR 目录
- `--suite <dir>` 指定套件构建目录，若无明确要求，套件存放在 `<verify_ip_workspace>/<tool_name>_suite/`

若存在之前已生成的套件文件，则需要用户明确是否允许在原套件基础上继续执行验证任务，或是明确允许删除原套件重新生成
否则不能轻易删除或覆盖原有套件，而应另行创建新的套件目录

初始套件将包含以下内容：
```
<suite>/
|   suite.json
|   cases_tmpl.c
```

### step-2 编写验证驱动文件

验证驱动模板用注释说明了待验证的性质，仅含注释，未包含实际的 C 代码。
当前步骤需结合 IP 的源码实现，把注释提示转换成代码，生成各个原 case 的验证驱动 `<case_name>.c`
`<case_name>` 直接使用 `cases_tmpl.c` 中的函数名

原则：必须严格按照注释提示转换代码，使得验证断言与文档中描述的性质完全一致
注释提示内容由 IP 源形式模型规约文档转换而来。若源文档存在错误，则注释提示内容也会跟着有错。
规约文档存在内容错误是 IP 设计中的潜在问题，应该由验证工作流来发现，当前阶段不要掩盖错误。

功能性验证 case 的驱动示例：
```c
#include "..."

void case_xx(void) {
    IP ip; // 初始化 IP，必须初始化所有非输出端口
    ip.xxx = ...;

    // 根据注释提示中的 assume 和 assert，补充正确的前、后置条件
    assume(...);
    IP_Func(&ip); // 调用 IP
    assert(...);  // 转换为对应验证工具支持的断言函数
}
```

非功能性验证 case 只检查编程语言层面问题，不含业务相关的 assume 和 assert，示例：
```c
#include "..."

void case_nf(void) {
    // 补充 C 代码：初始化 IP 并调用
}
```

必要时，允许自定义与验证任务相关的辅助宏或函数，保存到 `<cbmc_suite>/helper.c (.h)` 中

不同验证工具对 case 驱动文件的要求详见 `<skill>/references/<tool_name>/make_driver.md`

### step-3 编写验证配置

当前步骤任务：为待验证的 case 创建对应的配置文件，配置文件的通用结构如下：
```json
{
  "splited_from": <null|str>,
  "reduced_from": <null|str>,
  "py_subprocess": {
    "timeout": <int>
  },
  ...
}
```
字段说明：
- `splited_from` 若当前 case 是由原 case 等价拆分出的 sub-case，则填写原 case 名称；否则填 `null`
- `reduced_from` 若果当前 case 是缩减验证范围得到的 reduced-case，则填写原 case 名称；否则填 `null`
- `py_subprocess` 填写 python `subprocess.run()` 的配置项
- `py_subprocess.timeout` 填写命令执行限时，单位：秒
    默认 600 秒，根据实际 IP 代码内容和验证情况灵活调整，验证超时则尝试适当增加限时

不同验证工具的专属配置项，详见 `<skill>/references/<tool_name>/run_<tool_name>.md`

### step-4 执行验证

使用 `<skill>/scripts/<tool_name>/run_<tool_name>.py` 执行验证
脚本参数：
- `--suite <dir>` 指定验证套件目录
- `--case  <str>` 指定验证 case 的名字（例如 `case_1`，脚本会自动寻找 `<suite>/case_1.json`）
脚本将简要打印工具的执行结果，完整结果将保存（覆盖写入）到 `<suite>/output/<tool_name>/<case_name>/` 目录，其中：
- `result.json` 是 SKILL 内部脚本对该工具输出的简要分析
- 其他输出内容因工具而异

必须使用 `run_<tool_name>.py` 执行 case 验证并指定限时，禁止在命令行直接调用验证工具。
脚本会处理工具执行超时的情况，也会对该工具输出的简要分析。

错误处理：
- 预处理、编译和链接错误：
    先直接使用原始文件路径进行编译。遇到错误时依次区分 include/预处理失败、声明或类型/原型缺失、编译错误和链接定义缺失，再作最小处理。
    优先通过 `-I` 或加入真实依赖实现解决问题。仅缺少声明但真实定义存在时，可在 `<suite>/patched/` 的最小副本或 wrapper 中补充与定义完全一致的声明；
    禁止直接修改原始文件。`patched/` 只保存参与验证模型的最小复制件、wrapper、声明补丁或 stub，并必须在报告中说明差异和对可信度的影响。
    不得修改控制流、表达式、常量、类型宽度、限定符、边界判断或业务逻辑来使验证通过；这类改变若确有必要，只能作为明确受限的建模或 reduced-case。
    若 IP 实现本身存在无法修复的语法错误，则中止验证任务并如实报告无法得出结论。
    禁止修改 IP 实现，即使代码中有明显语法错误或逻辑错误也禁止修改！IP 实现中的逻辑错误是验证目标的一部分，应交由验证工具处理。
- 函数缺失
    若 IP 调用了找不到函数源码实现的外部库函数，可尝试自行创建函数，添加到 `patched/` 目录
    * 已明确功能且逻辑简单的函数，则自行补充实现，例如：简单工具函数，辅助判断函数
    * 若该函数代码实现可能涉及分支和循环，而验证目标只需要它满足某些基本性质，而不关心内部实现，则可使用 assume 和 assert 约束返回值范围
    * 遇到无法可信建模的复杂函数，则中止 case 验证
    自定义函数的实现细节需在最终报告中注明，并说明验证结论是否受自定义函数实现的影响
    若断言失败发生在自定义函数中，则需检查自定义函数的实现是否正确，或是否需要进一步约束返回值范围

### step-5 根据实际结果情况，灵活调整验证策略

Agent 的目标是验证所有的原 case，即 `cases_tmpl.c` 提及的所有 case。
若 case 过于复杂，工具无法得出结论，Agent 应积极调整策略。可以尝试拆分 case 或缩减验证范围，详见 `<skill>/references/ip/case.md`
针对不同验证工具，对应的验证策略调整指导和错误处理，详见 `<skill>/references/<tool_name>/run_<tool_name>.md`

尽可能验证所有 case 并得出有效结论！

### step-6 分析验证结果，给出 AI Agent 结论

读取 `<suite>/output/<tool_name>/<case_name>/result.json` 快速了解结论；
需要进一步分析原因时，根据不同的验证工具的分析方式不同，详见 `<skill>/references/<tool_name>/analyze_<tool_name>_output.md`

Agent 需对每个 case 的验证结果和整体验证情况进行综合分析，给出 JSON 和 Markdown 格式的结论，用于整合到最终报告中
Markdown 不要嵌入图片和 HTML，使用标题从 h3 开始（最终报告 HMTL 模板中已包含章节标题）

Agent 的输出内容保存到 `<suite>/output/ai_agent/` 目录中

可选择创建 `<case_name>.md` 说明该 case 的验证情况，没有必要补充时不创建。
应积极分析验证发现反例的 case、无法得出结论的 case，以及调整过验证策略的 case
可以说明：策略调整、拆分或缩减范围的原因与依据、未通过性质、反例关键变量与潜在风险、建模假设、验证边界及其对结论的影响等

必须创建 `conclusion.json`，为整体以及每个实际存在的 case 分别给出结论：
```json
{
  "overall": {
    "functional":    "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS",
    "nonfunctional": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
  },
  "cases": {
    "<case_name>": "INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS"
  }
}
```
字段说明：
- `overall.functional` 给出功能性整体验证结论，只能选用给定的枚举值
- `overall.nonfunctional` 给出非功能性整体验证结论，只能选用给定的枚举值
- `cases` 各case 的验证结论，必须覆盖 suite 中参与验证的每一个 case
    键为 case 名称，值为 AI Agent 给出的结论（根据验证策略的调整情况和工具给出的来给出结论）
关于 case 结论和整体验证结论的判断标准，详见 `<skill>/references/ip/case.md`

必须创建 `conclusion.md`，依次说明总体评价、验证范围、失败性质、潜在风险、建模限制和结论依据，其他内容可自行灵活补充

可选择创建 `issues.md` 总结存在需报告的问题和处理情况，若没有异常处理则不创建该文件。
重点给出与待验证 IP 自身导致的问题，或是与验证流程相关的问题，如：
- IP 自身导致的编译/链接/环境问题、驱动或配置文件错误，IP 文档或代码内容相关问题等
- 工具无法得出结论，或是验证策略调整的原因、依据和处理方式
- SIKLL 本身指导不明确或有误，导致无法完成验证任务或验证结果不完整的情况
- 只汇报验证过程中的、已出现的状况，不要猜测可能出现的异常或问题

必须创建 `experience.md`，要求内容详尽、明确、可操作，可作为提示词指导下一轮的 Agent 验证任务，例如：
- 哪些性质或 case 验证困难，原因是什么
- 遇到的问题属于实现、规约、IR、驱动、配置、工具、环境还是 SKILL
- 为每个重要问题尝试过哪些方案，按先后说明关键配置或建模方式
- 哪些方案有效或无效、为什么、边界是什么，下次要避免哪些无用尝试
- case 是否拆分或缩减，覆盖完整性和结论可信度受到什么影响
- 已解决和未解决的问题分别是什么，未解决项下一步应探索什么
- 下次验证同一 IP 时应优先检查哪些规约依赖、定义域、循环界、输入约束、stub 或补丁
- 可复用的驱动结构、验证工具的配置、反例分析方法和验证顺序

### step-7 生成最终验证报告

使用 `<skill>/scripts/<tool_name>/make_report.py` 生成验证报告，
脚本参数：`--suite <suite>` 指定验证套件目录

脚本将从各 case 的配置文件和验证结果中机械提取验证参数、验证结果（断言列表、反例路径）等内容，
并将 AI Agent 的分析结果内容则插入报告对应板块

最终报告将保存到 `report.html` 和 `report.json`
