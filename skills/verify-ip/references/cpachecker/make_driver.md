# 验证驱动编写指南

## 断言与 specification 匹配

容器预处理环境无法提供 `<assert.h>`，使用与当前断言 specification 匹配的最小 shim：
```c
extern void __assert_fail(const char *, const char *, unsigned int, const char *);
#define assert(cond) ((cond) ? (void)0 : __assert_fail(#cond, __FILE__, __LINE__, __func__))
```
运行日志若警告 specification 未监视该目标函数，本次结果不可用，必须先修正断言与 specification 的匹配关系。
若 specification 已监视 `__assert_fail`，但具体分析 CPA 仍报告未知函数调用、忽略副作用或 soundness warning，
不要把它误判为 specification 失配；应在分析中披露，并结合反例路径或负向探针确认断言目标有效。

功能性 case 必须验证模板中的真实后置性质，不能用恒真表达式或无关断言占位。

若实现可以由驱动安全地 `#include`，优先采用单翻译单元：驱动 include 真实实现 `.c`，配置的 `files` 只列驱动文件。
这样仍验证原始实现，同时避免预处理后的多个翻译单元触发 CFA 位置映射异常。
include 路径必须依赖 runner 的只读挂载和 `-I`，不得写宿主绝对路径。若实现不适合直接 include，再把实现和驱动分别列入 `files`；
出现 CPAchecker 内部多翻译单元解析异常时，改回单翻译单元 wrapper。

必要时，允许自定义与验证任务相关的辅助宏或函数，保存到 `<suite>/helper.c (.h)` 中

## 前后置断言

若注释给出的是合法的 C 语言表达式，则严格按照注释内容进行转换。
顶层合取可以在同一驱动、同一次执行和同一组共享变量/见证下写成多条断言。
示例：
```c
// assume !(a == 0) && x > 0 && y > 0
// assert !(s > 0 || t != 0)

// 正例
__VERIFIER_assume(!(a == 0));
__VERIFIER_assume(x > 0);
__VERIFIER_assume(y > 0);
assert(!(s > 0 || t != 0));

// 反例：未严格按照注释提示补充断言。禁止转换表述，即使语义等价的转换也不允许
__VERIFIER_assume(a != 0);
assert(s <= 0);
assert(t == 0);
```

使用注释中的变量名和常量值，不要替换。示例：
```c
// assert a == FALSE_ && b == 1
// 已知宏 FALSE_ 定义为 0，宏 TRUE_ 定义为 1
// 正例：使用断言中的变量名和值
assert(a == FALSE_ && b == 1);
// 反例：禁止替换常量和字面量值
assert(a == 0 && b == TRUE_);
```

## 变量名转换

使用 IP 的成员变量名，示例：
```c
// assume a > BB

// 正例（若 a 是 IP 成员变量，BB 是常量枚举）
__VERIFIER_assume(ip.a > BB);
// 反例
__VERIFIER_assume(a > 1);
```

contract.json 中可能出现 IP struct 中不存在的辅助变量（如 `Gi_out'`，对应"输出端口副本"），这类变量通常与某个 state 成员等价，在规约中形式化地区分输入副本和状态更新结果。处理方式：查看规约对该变量的约束，映射到实现中实际存在的对应成员，并在报告中说明映射关系。

## 新旧值

`a` 和 `a'` 分别表示同一变量的旧值和新值。比较新旧值时，需新建变量 `old_xxx` 保存旧值。注意旧值变量必须在函数开头声明（C89 规范）：
```c
// assert a' == a + 1

// 正例：在函数块开头声明 old_a，在调用前赋值
int old_a;
old_a = ip.a;
IP_Func(&ip);
assert(ip.a == old_a + 1);
```

后值变量 `a'` 有时也出现在规约的判别条件中（如 `assert a' > N && ...`）。若同一规约中存在对 `a'` 的显式约束（如 `a' == a + 1`），可将判别条件中的 `a'` 替换为等价的旧值表达式：
```c
// assume 条件中含 a'：(a' > N) && (a' == a + 1)
// 可改写为前置 assume：
__VERIFIER_assume((ip.a + 1) > N);
IP_Func(&ip);
assert(ip.a == ip_old_a + 1);  // 验证 a' 的具体值
```

## 规约布尔 → C 整型

若 IP 实现用整型存储布尔值，使用 C 语义映射：`true` → 非零即真（`x`），`false` → 零为假（`!x`）。
禁止硬编码与 0/1 比较，因为实现中可能使用非标准值（如 `TRUE32 = 0xEB90146F`）：
```c
// assert flag' == true
// 正例：使用 C 语义，非零为真
assert(ip.flag);
// 反例：禁止硬编码比较
assert(ip.flag == 1);
```

## 数组、结构体、容器

`{x: s,y: t}` 字面量根据实际类型转换：数组→下标访问，结构体→成员访问，容器→get 函数。示例：
```c
// assert a == {0: x,1: y}
// assert b == {s: x,t: y}

// 正例（若 a 是数组，b 是结构体）
assert(ip.a[0] == x);
assert(ip.a[1] == y);
assert(ip.b.s == x);
assert(ip.b.t == y);
```

## 数组长度

`len(a)` 和 `size(a)` 转为 `sizeof` 表达式：
```c
// assume len(a) == N
__VERIFIER_assume(sizeof(ip.a) / sizeof(ip.a[0]) == N);
```

若 `a` 是数组指针，优先使用栈内分配内存：
```c
// assume len(a) == N
// assert len(a') == M

// 正例（若 a 是 int* 指针）
int a[N];  // 注意：N 必须是编译期常量，否则使用具体数值
__VERIFIER_assume(sizeof(a) / sizeof(a[0]) == N);
ip.a = a;
IP_Func(&ip);
assert(sizeof(a) / sizeof(a[0]) == M);
```

当 sizeof 结果与规约 len 值不符时（例如规约说 `len(angle) == 2` 但实现是 `float angle[3]`），
验证会得到 FALSE。这类结果可能反映规约与实现之间的结构差异（规约用"有效分量数"，实现用物理数组大小），
需要人工判断是规约错误还是实现错误，在验证报告中注明，不要直接当作实现 bug 处理。

## 全称量词

优先转为符号化验证条件（range 为前闭后开区间）。注意循环变量必须在函数开头声明：
```c
// forall ( var: i, range: from 0 to 9 step 1 ) { assert a[i] == 0 }

// 正例：符号化验证条件（C89 要求变量在函数开头声明）
int i;
i = __VERIFIER_nondet_int();
__VERIFIER_assume(0 <= i && i < 9);
assert(ip.a[i] == 0);

// 正例：显式展开固定小范围
assert(ip.a[0] == 0);
...
assert(ip.a[8] == 0);
```

无界量词若有隐含边界，取合理边界值并在报告中说明。

当需要验证 IP 内部循环对所有元素执行后的性质时，应确保 assume 对所有 i 同时成立（使用循环或展开），而非仅约束单个符号下标。

若量词体内涉及浮点数组元素的乘除法运算，符号化 nondet 索引方式下 BMC 的求解可能超时。此时参照 `run_cpachecker.md` 的调整策略，优先改为显式展开，或等价拆分性质；若必须固定具体值或缩小范围，应创建 reduced-case 并披露覆盖局限。

## 存在量词

由规约完全定义的见证变量，直接构造见证值；由规约部分定义的，已约束部分直接赋值，未约束部分用 `__VERIFIER_nondet_xxx()` 填充。

若见证变量可由规约直接定义，应在驱动中显式构造该值并断言其性质。此时 IP 调用不一定必要（若断言完全不依赖 IP 输出），但保留 IP 调用也不影响结论：

若变量由 IP 计算产生且其值可通过输入确定，先调用 IP 再用 nondet + assume 建模：
```c
// exists ( var: y; type: float ) { assert output' == f(y) }

IP_Func(&ip);
float y = __VERIFIER_nondet_float();
__VERIFIER_assume(/* 约束 y 的条件，如 y 在某个范围内 */);
assert(ip.output == f(y));
```

若见证变量是 IP 内部不可观测的中间值（例如从 volatile 硬件寄存器读取并计算的中间结果），上述规则无法直接应用，按以下顺序尝试：
1. 在 `patched/IP.c` 中暴露内部变量（添加全局输出变量或 getter），使驱动可以获取中间值
2. 在 `patched/IP.c` 中去除相关 volatile 声明，在驱动中通过直接赋值或 nondet + assume 控制硬件读取值，从而使 IP 内部计算路径可预测
3. 若上述方式均导致 CPAchecker 超时或 UNKNOWN，将该 case 标记为无法有效验证，在报告中说明规约存在量词性质在当前模型下的局限性；若存在可信的有限拆分或范围缩减方案，按派生 case 规则继续尝试

修改 patched/ 中的 volatile 声明必须在报告中注明，并说明验证结论适用于等效的非 volatile 建模。

## volatile 变量

IP 可能通过 volatile 声明的变量或数组读取硬件数据（如 `volatile uint8 XBYTE[0xFFFF]`）。
CPAchecker 将每次 volatile 读取建模为独立 nondet 值，无法通过 assume 约束其内容。

若验证目标不依赖硬件读取的具体值，可保持 volatile 不变，让 CPAchecker 对其进行符号化分析。

若验证目标需要约束硬件读取值，可在 `patched/IP.c` 中去掉相关 volatile 声明，并在驱动中通过 nondet + assume 初始化这些变量。此修改必须在报告中注明。

## 浮点数

CPAchecker 对浮点符号化支持有限。对所有 nondet float/double 变量，在声明后立即添加 NaN/Inf 排除 assume，这是编写浮点验证驱动的第一步，不要遗漏：
```c
float x = __VERIFIER_nondet_float();
__VERIFIER_assume(x == x && -3.4028235e38f < x && x < 3.4028235e38f);
double y = __VERIFIER_nondet_double();
__VERIFIER_assume(y == y && -1.7976931348623157e308 < y && y < 1.7976931348623157e308);
```

旧值变量若需精确比较，也须排除 NaN（NaN != NaN 会导致精确比较失败）：
```c
float old_x;
old_x = ip.x;  // 若 ip.x 来自 nondet 浮点且需精确比较，应确保 ip.x 已通过 NaN 排除
```

直接赋值用精确比较，计算结果用误差范围：
```c
assert(ip.x == X);                    // 直接赋值，精确比较
assert(fabsf(ip.z - a*b) < 1e-6f);  // 计算结果，近似比较
```

断言中的数学式与实现使用相同运算顺序且运算简单时，可先尝试精确比较；若因浮点舍入得到不符合规约意图的反例，再改用有明确依据的误差范围，并在报告中说明。

## 链式表达

提示中可能使用链式表达式，例如 `a > b > c`，需拆分成多条断言，示例：
```c
// assert a > b > c
// 正例
assert(a > b && b > c, "...");
// 反例：在 C 语言中，a>b>c 会被解析为 a>b>c，无法正确表达断言语义
assert(a > b > c, "...");
```
## 文本或 LaTeX

模板中的断言可能包含文本或 LaTeX 公式，需理解其语义，转换成等价的 C 代码表达式，必要时自定义辅助函数。

## 时序控制

`clock' = clock` 表示 IP 不涉及时序控制相关的行为，无论该条件出现在合取式的哪个位置，均直接忽略，不写对应的 assert。

- 若 case 的全部性质均为时序约束，则只添加 `assert(1)` 占位
- 若 case 是时序约束与其他性质的合取，忽略时序部分，其余性质照常转换为断言

## 兜底规则

若出现上述规则以外的情况，可自行转换，并给出你的转换思路，在最终验证报告上指出。
