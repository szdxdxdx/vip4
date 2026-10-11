
# 验证 case

所有验证工作流都包含两类验证：
- 功能性验证：验证 IP 实现是否满足形式规约描述的行为（前后置断言）
- 非功能性验证：检查数组越界、指针越界、整数溢出等与业务逻辑无关的编程语言层面问题

功能性和非功能性需求将被拆分出多个小的验证 case 来单独验证

## 基本概念

- 原 case：
    从 IP 形式规约中提取而来的 case
    在构建验证套件时，SKILL 内部脚本会根据待验证 IP 的形式规约（实际使用的是由 IP 转换而来的 IR），得到若干个验证 case
    这些 case 直接对应于原始规约中的性质，是验证的根目标
- sub-case：
    当 case 的验证目标过于复杂时，可以等价拆分为多个 sub-case。所有 sub-case 合在一起与拆分前的 case 等价
- reduced-case：
    当 case 的验证目标过于复杂时，可以缩小验证范围得到 reduced-case，寻求局部结论
- 父 case：
    相对于某个 sub-case 或 reduced-case 的直接父 case

## case 命名规则

`<case_name>` 命名规则为 `case(_nf)?(_\d+)?((_R|_S)(_\d+))*`
- `_nf` 表示非功能性验证，缺省则表示功能性验证
- `_\d+` 数字仅用作编号
- `_S` 表示拆分出来的 sub-case
- `_R` 表示缩减验证范围得到的 reduced-case

## 验证策略调整规则

Agent 的目标是验证所有的原 case，若 case 可以得出结论，那就不用派生出 sub-case 或者 reduced-case；

若在验证某一个 case （不论是原 case 还是派生出的 case）时，若无法得出结论（工具执行超时等），
应积极调整验证策略，派生新的 case 进行验证，推导出父 case 的结论

### 拆分 case

目标过于复杂时，可以等价拆分为多个 sub-case。所有 sub-case 的验证结论，可以推导出父 case 的结论
没有遗漏分支、增加前提或缩小输入范围

sub-case 命名为 `<原case>_S_<数字编号>`，例如 `case_1` 拆分出多个 sub-case 得到 `case_1_S_1`、`case_1_S_2` 等。
配置中填写 `splited_from`

对于某些验证工具，可能需要编写不同的验证配置文件，启动不同的参数来多角度验证，此时应拆分 sub-case，分别对应不同的配置

### 缩减 case

无法完成原范围验证时，可以创建 reduced-case，缩小验证范围（修改后不是让 case 更正确，而是更受限）。
reduced-case 的结论只在缩减范围内成立，不能代替父 case 的完整结论。

reduced-case 命名为 `<原case>_R_<数字编号>`，例如 `case_1` 缩减验证范围，尝试不同程度的调整方案，得到多个 reduced-case `case_1_R_1`、`case_1_R_2` 等。
配置中填写 `reduced_from`

可以调整 .json 配置`--unwind`、`timeout` 或其他配置参数，或是调整 .c 驱动断言的断言内容

### 综合使用两种调整策略

派生出新的 sub-case 或 reduced-case 时，可以仅修改验证配置，或仅修改验证驱动，或同时修改两者
优先考虑等价拆分 sub-case

原 case、sub-case 和 reduced-case 都视作独立的验证 case，拥有独立的验证驱动和验证配置。
每个 case 都必须有成配套的验证驱动 `<case_name>.c` 和验证配置 `<case_name>.json` 文件。

每个 case 的驱动和配置文件必须保留，供后续分析使用。
若驱动或配置本身有误（笔误）则可直接修改文件，否则拆分 sub-case 或创建 reduced-case 后，原 case 驱动和配置文件不再修改。

示例：
```
<suite>/
|   # 原始验证驱动和配置
|   case_1.c
|   case_1.json
|   case_2.c
|   case_2.json
|
|   # 因 case_1 目标过于复杂，对其进行等价拆解，得到 S1 和 S2 两个 sub-case
|   case_1_S_1.c
|   case_1_S_1.json
|   case_1_S_2.c
|   case_1_S_2.json
|
|   # 因 case_1_S_2 仍难以验证，故缩减验证范围，寻求局部结论
|   case_1_S_2_R_1.c  
|   case_1_S_2_R_1.json
|
|   # 因 case_2 目标过于复杂，尝试寻求局部结论，采用两种不同的缩减方案
|   case_2_R_1.c
|   case_2_R_1.json
|   case_2_R_2.c
|   case_2_R_2.json
```

sub-case 和 reduced-case 可以多级派生，例如 `case_1_S_1_S_1_R_1` 等。

## Agent 的验证结论分析

Agent 给出的 case 的验证结论可以是 `INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS`，
父 case 的结论需要结合其派生 case 的结论进行综合分析，推导出父 case 的最终结论。
规则如下（从上往下按优先级）：
1. INCONCLUSIVE
    编译失败、链接失败、环境缺失，且无法修复。工具运行异常、崩溃、模型不一致，导致结果不可用
2. FAIL
    没有因为编译/链接/环境错误导致的中断
    断言失败，验证工具明确给出反例
3. TIMEOUT
    验证工具执行超时，未产出任何最终结果
4. PARTIAL_PASS
    当前 case 没有得出验证结论，派生 case 有明确的验证结论，但派生 case 验证覆盖不完整
5. PASS
    验证工具没有发现反例
    或是所有派生 case 都使用完整可信的验证策略，且没有发现反例

Agent 给出的整体验证结论可以是 `INCONCLUSIVE | FAIL | TIMEOUT | PARTIAL_PASS | PASS`，
规则如下（从上往下按优先级）：
1. INCONCLUSIVE
    编译失败、链接失败、环境缺失，且无法修复。工具运行异常、崩溃、模型不一致，导致结果不可用
2. FAIL
    没有因为编译/链接/环境错误导致的中断
    至少一个原 case 断言不通过，出现明确反例，证明实现违反规约
    某些 case 虽未完全执行，但已确认存在错误路径，足以构成规约不满足
3. TIMEOUT
    存在至少一个原 case 因超时未产出任何最终结果，其他已完成的 case 没有断言失败
    超时前没有得到足以判定失败的反例
4. PARTIAL_PASS
    不存在原 case 断言失败，所有原 case 都有最终结果，但验证覆盖不完整
    所有原 case 的断言均通过，但验证覆盖不完整，例如：
    某些原 case 原本无法直接证明，但通过弱化验证目标或减少验证范围后才得到通过
    部分原 case 原完整的验证策略超时，调整了验证策略缩小验证范围后验证通过
    因超时、状态爆炸等原因，调整策略后仅覆盖了部分验证空间
5. PASS
    所有验证原 case 都使用完整且可信的验证策略，断言全部通过，得到有效结论

## 验证策略调整指南

### 修改验证配置

优先考虑修改验证配置文件 `<case_name>.json`，例如：
验证超时可适当增加 `timeout`、调整循环展开的上限、调整验证工具的分析策略、增加资源限制等

若验证配置修改后仍无法得出结论，则尝试修改验证驱动 `<case_name>.c`

### 拆解复杂的合取式

可以将复杂的合取式拆解为多个子 sub-case，示例：
```
case_1:
  // assert P && Q && R

case_1_S_1:
    // assert P
case_1_S_2:
    // assert Q
case_1_S_3:
    // assert R
```
结论分析：
任一 sub-case FAIL，则父 case FAIL
所有 sub-case PASS，则父 case PASS
其余情况无法得出结论 INCONCLUSIVE

### 拆解复杂的析取式

可以将复杂的析取式拆解为多个子 sub-case，示例：
```
case_1:
    // assert P || Q || R

case_1_S_1:
    // assert P
case_1_S_2:
    // assert Q
case_1_S_3:
    // assert R
```
结论分析：
任一 sub-case PASS，则父 case PASS
所有 sub-case FAIL，则父 case FAIL
其余情况无法得出结论 INCONCLUSIVE

## 拆解 if-else

断言中的 `if C then P else Q` 并非表达程序的执行流程，而是逻辑上的条件分支，
等价于 ```(C => P) && (!C => Q)`，可以将 `C` 转换为 `assume`，示例：
```
case_1:
    // assert if C then P else Q

case_1_S_1:
    // assume C
    // assert P
case_1_S_2:
    // assume !C
    // assert Q
```
结论：
仅当两个 sub-case 都 PASS，父 case 才 PASS；
任一 sub-case FAIL，则父 case FAIL；
其余情况无法得出结论 INCONCLUSIVE

### 拆解存在量词

存在量词一般不能像合取/析取那样直接等价拆成多个独立 case 并简单合并结论
如果要拆，只能围绕同一个 witness（见证）来做分阶段验证，且通常只能作为辅助分析

存在量词下的合取范式可以如下拆解：
```
case_1:
    // assert exists( x ){ P(x) && Q(x) }

case_1_R_1:
    // assert exists( x ){ P(x) }
case_1_R_2:
    // assert exists( x ){ Q(x) }
```
结论：
所有 reduced-case PASS，且是同一个 x 全部满足，则父 case PASS；
所有 reduced-case PASS，但不是同一个 x ，则父 case PARTIAL_PASS；
任一 reduced-case FAIL，即找到反例，则父 case FAIL；
其余情况无法得出结论 INCONCLUSIVE

---

存在量词下的析取范式可以如下拆解：
```
case_1:
    // assert exists( x ){ P(x) || Q(x) }

case_1_R_1:
    // assert exists( x ){ P(x) }
case_1_R_2:
    // assert exists( x ){ Q(x) }
```
结论：
任一 reduced-case PASS，即找到反例，则父 case PASS；
所有 reduced-case FAIL，且是同一个 x 全部满足，则父 case FAIL；
其余情况无法得出结论 INCONCLUSIVE

---

可以根据源码分析，选取某一个具体的值或范围 witness 来拆解存在量词，从而得到准确的验证结论
可以通过多次尝试不同的 witness 来覆盖整个输入空间，
