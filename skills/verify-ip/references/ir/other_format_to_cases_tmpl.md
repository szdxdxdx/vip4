
# 将形式模型转换为 cases_tmpl.c

本说明指导 Agent 将 txt、JSON、Markdown、PDF、Word、图片或其他格式的形式模型转换为 `<ir>/cases_tmpl.c`。
模板不是可直接编译的驱动，而是保存规约原文并指导后续 Agent 编写验证驱动的中间表示。

## 转换前的工作

### 阅读全部输入

阅读全部形式模型文件，理解变量说明、状态表、图片文字、接口说明等内容。
不要只根据扩展名或文件名判断文件是否重要，也不要只阅读一个“看起来像主规约”的文件。
代码仅用于确认函数入口、结构体成员、变量类型和名称映射，不能用代码实际行为替换形式模型。

先整理性质清单，并为每条性质记录来源（文件、章节、表格行或条目）。至少检查：

- 输入范围、枚举值、互斥条件和环境约束；
- 初始化、调用前条件、指针和缓冲区要求；
- 返回值、输出端口、状态更新和错误码；
- 状态转移、状态保持和事件顺序；
- 不变量、边界值、空值、满容量和异常行为；
- 时序、协议、重复调用和多步序列性质；
- 形式模型明确要求的安全和非功能性性质。

若多个文件描述同一 IP， 则合并阅读。
文件之间出现矛盾时不得自行选择或修正，
如果是规约内容逻辑冲突，则如实保留，实际验证工具会汇报错误。
如果是规约无法形成有意义的性质，应停止转换并汇报错误。

## 模板格式

将待验证性质分为功能性验证和非功能性验证两类。
功能性验证相关的性质来自形式模型描述的业务行为、状态机、协议、时序逻辑和不变量等。
非功能性验证相关的性质于编程语言的检查越界、空指针、整数溢出等有关。

将待验证的性质拆成多个 case 函数，
功能性 case 从 `case_1` 开始连续编号，例如 `case_1`、`case_2`、`case_3` 等
非功能性 case 命名为 `case_nf`，通常非功能性 case 只需一个，若不然也自行增加编号。

每个功能性 case 必须同时包含原文内容和起指导意义的断言：
1. 原文：尽可能复制形式模型原文，保留变量名、单位、状态名、数学符号、撇号、新旧时刻和时序算子。
2. 指导：根据原文给出后续 Agent 应实现的 `assume` 和 `assert`。指导表达可以接近 C，但不要求符合验证工具语法。
原文层防止语义丢失，指导层帮助 Agent 写驱动；不能只留下翻译后的 C 表达式，也不能只写“见原文”。

通常非功能性 case 不需要原文和指导，因为验证工具本身就能检查越界、空指针、整数溢出等问题。
若有必要说明，也可以仿照功能性 case 的写法

示例（）：
```c
void case_1(void) {
    // [来源]
    // 文件：contract.txt；章节：Output；条目：O-1
    // [原文]
    // When 0 <= x <= 10, output = 2*x + 1.
    // [指导]
    // assume 0 <= x && x <= 10
    // assert output == 2*x + 1
}

void case_nf(void) {
}
```

所有非 C 内容必须在注释内。模板可以包含 Unicode、LTL、数学符号和工具暂不支持的语法，因为它是提示文件，不是驱动文件。

## 常见格式和转换示例

### 前置条件和后置条件

原文：

```text
Precondition: 0 <= len <= MAX_LEN
After process(buf, len), result == checksum(buf, len)
```

```c
void case_1(void) {
    // [原文]
    // Precondition: 0 <= len <= MAX_LEN
    // After process(buf, len), result == checksum(buf, len)
    // [指导]
    // assume 0 <= len && len <= MAX_LEN
    // assume buf points to a valid buffer containing len elements
    // assert after process(buf, len): result == checksum(buf, len)
}
```

输入合法范围和调用前资源有效通常是 `assume`；调用后的输出是 `assert`。

### 分段公式和边界

原文：

```text
f(x) = 2x+1, 0 <= x <= 10
f(x) = 21, x > 10
```

不同条件对应不同结果，应拆分：

```c
void case_1(void) {
    // [原文]
    // f(x) = 2x+1, 0 <= x <= 10
    // [指导]
    // assume 0 <= x && x <= 10
    // assert output == 2*x + 1
}

void case_2(void) {
    // [原文]
    // f(x) = 21, x > 10
    // [指导]
    // assume x > 10
    // assert output == 21
}
```

不能把它错误合并为 `assert output == 2*x+1 || output == 21`，否则丢失条件和结论的对应关系。

### 状态机或转移表

原文：

```text
IDLE + start -> BUSY
BUSY + done  -> IDLE
BUSY + fault -> ERROR
ERROR + reset -> IDLE
```

```c
void case_1(void) {
    // [原文]
    // IDLE + start -> BUSY
    // [指导]
    // assume state == IDLE
    // assume event == start
    // assert state' == BUSY
}

void case_2(void) {
    // [原文]
    // BUSY + done -> IDLE
    // [指导]
    // assume state == BUSY
    // assume event == done
    // assert state' == IDLE
}

void case_3(void) {
    // [原文]
    // BUSY + fault -> ERROR
    // [指导]
    // assume state == BUSY
    // assume event == fault
    // assert state' == ERROR
}
```

表格中明确列出的每条转移通常单独成 case。若原文还规定“未列出的事件保持原状态”，必须另写出该性质，不能自行推断未列出的组合是非法或不可能。

### 不变量和状态保持

原文：`At all times, 0 <= write_index <= capacity.`

```c
void case_4(void) {
    // [原文]
    // At all times, 0 <= write_index <= capacity.
    // [指导]
    // assume capacity >= 0
    // assert always 0 <= write_index && write_index <= capacity
}
```

“始终成立”不能无提示地改成某一次调用结束时成立。应保留 `always`、`at all times` 等范围，后续 Agent 再根据循环或多步调用建立验证场景。

### LTL 或其他时序逻辑

原文：

```text
G(request -> F response)
G(!error -> X ready)
```

```c
void case_5(void) {
    // [原文]
    // G(request -> F response)
    // [指导]
    // assume request is a valid request event
    // assert every request is eventually followed by response
}

void case_6(void) {
    // [原文]
    // G(!error -> X ready)
    // [指导]
    // assume current error == false
    // assert ready is true at the next step
}
```

不得把 `G(request -> F response)` 简化成当前调用结束时的 `assert response`；`G`、`F`、`X`、`U` 等算子表达跨时刻关系，必须在原文和指导层保留。

### JSON 或键值规约

原文：

```json
{"input":{"min":0,"max":100},"output":{"when":"valid","rule":"output=input*2"},"invalid":{"return":"ERR_RANGE"}}
```

```c
void case_7(void) {
    // [原文]
    // input: min=0, max=100; output: output=input*2 when valid
    // [指导]
    // assume 0 <= input && input <= 100
    // assume input is valid
    // assert output == input * 2
}

void case_8(void) {
    // [原文]
    // invalid: return=ERR_RANGE
    // [指导]
    // assume input < 0 || input > 100
    // assert return_value == ERR_RANGE
}
```

保留 JSON 字段名和原始值；字段到 C 成员的具体映射交给后续 Agent，不要根据猜测改名。

### 协议和输入序列

原文：`After START, DATA is accepted. STOP is accepted only after at least one DATA. After STOP, emit DONE and return IDLE.`

```c
void case_9(void) {
    // [原文]
    // After START, DATA is accepted.
    // [指导]
    // assume current state == IDLE
    // assume event == START
    // assert next state accepts DATA
}

void case_10(void) {
    // [原文]
    // STOP is accepted only after at least one DATA.
    // [指导]
    // assume at least one DATA was accepted
    // assume event == STOP
    // assert STOP is accepted
}

void case_11(void) {
    // [原文]
    // After STOP, emit DONE and return IDLE.
    // [指导]
    // assume STOP was accepted
    // assert DONE is emitted
    // assert next state == IDLE
}
```

“至少一次”“之前已经发生”“直到”等历史条件不能被当前输入值替代。

## assume、assert 和 case 的判定

`assume`：输入范围、环境约束、调用前有效性、当前状态、触发事件和为覆盖某分支而固定的场景条件。
`assert`：返回值、输出、状态更新、调用后不变量、错误码、状态机目标状态和时序结论。

不要机械转换语句。例如：

```text
Caller shall provide x >= 0.
```

是 `assume x >= 0`；但：

```text
For x < 0, the function shall return ERR_INVALID.
```

是 `assume x < 0` 加 `assert return_value == ERR_INVALID`。若原文无法判断某条件是环境前提还是实现责任，保留原文并标注“语义需确认”，不要静默选择。

应拆分 case 的情况：不同条件对应不同结果、正常和异常路径、不同状态转移、不同错误码、相互独立的不变量，以及需要不同调用序列的性质。

不应拆分的情况：同一次调用必须共同成立的多个输出、同一状态转移的触发条件和目标状态、一个不可分的协议序列。比如“输入有效时返回 OK 且状态变为 READY”必须放在同一个 case 中。

## 语义保真规则

- 不得删除单位、量词、边界、条件分支、时序范围或状态历史；
- 不得把 `x'` 改成 `x`，不得把下一时刻改成当前时刻；
- 不得把等式、赋值、蕴含或等价关系混为一谈；
- 不得根据代码修正文档错误、补充文档没有写出的前提或缩小输入范围；
- 不得用 `assert true`、`assert property holds` 或“见原文”替代具体性质；
- 不得把业务安全性质全部放入 `case_nf`；明确的业务性质必须有功能性 case；
- 只将性质和指导写在注释中，模板不要求可编译。

## 完成检查

生成后确认：

1. 已阅读全部形式模型及相关说明；
2. 每个 case 都能追溯到具体来源；
3. 原文层和指导层均存在，且语义一致；
4. 前提、触发条件、结论、边界、异常、状态和时序性质没有遗漏；
5. `case_1` 至最后一个功能性 case 连续编号，并存在 `void case_nf(void)`；
6. 所有非 C 内容都在注释中；
7. 文件保存为 `<ir>/cases_tmpl.c`；
8. 执行 `<skill>/scripts/ir/check_ir.py --ir <ir>`。

若输入缺失、内容无法理解，或已确认的文件冲突导致无法形成可靠性质，应停止生成并将已确认的问题写入 `<ir>/error_report.md`，不要猜测或编造规约。
