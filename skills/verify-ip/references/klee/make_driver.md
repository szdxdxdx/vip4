# 验证驱动编写指南

功能性 case 必须验证模板中的真实后置性质，不能用恒真表达式或无关断言占位

## 符号化策略

KLEE 通过 `klee_make_symbolic` 将内存区域标记为符号量，再自动探索所有可行路径。

`klee_make_symbolic` 要求第一参数是独立内存对象的起始地址（栈上独立变量或 malloc 分配的堆内存），不能传入结构体内部字段的地址，否则 KLEE 报 `invalid pointer: make_symbolic`。

推荐优先使用整体符号化策略，对 IP 结构体整体调用 `klee_make_symbolic`，但有如下限制：

- 只对输入端口和状态变量符号化，不要对输出端口做 `klee_make_symbolic`（输出端口由 IP_Func 写入，不需要符号化初始值）
- 若 IP 结构体不含指针，可整体符号化，再用 `klee_assume` 约束输入端口范围
- 若 IP 结构体含指针成员（函数指针、数据指针等），不能整体符号化

整体符号化示例（结构体不含指针）：
```c
IP ip;
klee_make_symbolic(&ip, sizeof(ip), "ip");
klee_assume(ip.input_port >= MIN && ip.input_port <= MAX);
// 无需初始化输出端口，IP_Func 会写入
```

含指针成员时，逐字段处理：先初始化所有指针字段（赋值有效地址或置 NULL），再对各标量/数组输入端口分别符号化：
```c
IP ip;
// 先初始化指针字段（必须先于其他字段操作）
ip.fun = IP_Func;           // 函数指针
uint8_t buf[N];
ip.data_ptr = buf;          // 数据指针指向独立分配的内存

// 再符号化标量型输入端口（用独立变量，不能传 &ip.field）
int input_val;
klee_make_symbolic(&input_val, sizeof(input_val), "input_val");
ip.input_field = input_val;

// 数组型输入端口（嵌入在结构体内的固定数组字段，如 float Gi[3]）：
// 不能直接传 &ip.Gi，必须用独立数组逐元素赋值
float Gi[3];
klee_make_symbolic(Gi, sizeof(Gi), "Gi");
ip.Gi[0] = Gi[0]; ip.Gi[1] = Gi[1]; ip.Gi[2] = Gi[2];

// 指针型数组字段：符号化独立数组后赋给指针字段
klee_make_symbolic(buf, sizeof(buf), "buf");
```

## volatile 变量处理

IP 可能通过 `volatile` 修饰的全局变量读取硬件数据（如 `volatile uint8 XBYTE[0x10000]`）。KLEE 无法对 volatile 读取自动引入符号量，每次读取结果均被具体化为确定值，无法探索不同输入下的路径。

若验证目标需要约束硬件读取值，须创建 `patched/` 版本的实现文件，去掉相关 volatile 声明，使 KLEE 可以符号化控制这些输入：
1. 将 IP 的 `.c`（和必要的 `.h`）复制到 `<klee_suite>/patched/` 目录
2. 在 patched 版本中去掉 volatile 修饰：`volatile uint8 XBYTE[]` → `uint8 XBYTE[]`
3. 在驱动文件中 include patched 版本的实现文件，而不是原始文件
4. 在驱动中对相关数组调用 `klee_make_symbolic` 进行符号化
5. 必须在验证报告中注明此修改，并说明验证结论适用于等效的非 volatile 建模

若验证目标不依赖硬件读取的具体值，可以保留 volatile，让 KLEE 使用具体化的默认值探索。

patched 方案中，驱动与 patched 实现之间的桥接有两种方式：

**方式一（推荐）：通过全局变量传递读取值**

在 patched 实现中，将 volatile 数组成员或变量的读取替换为全局变量的引用：
```c
// patched/ip.c（去掉 volatile 声明）
unsigned char hw_region[REGION_SIZE];  // 原 volatile 已去除

// 新增：驱动可设置的符号化值，每个被读取的地址对应一个全局变量
unsigned char sym_read_1;
unsigned char sym_read_2;

void IP_Func(void *p) {
    ...
    val = sym_read_1; // 代替 hw_region[ADDR_1]
    val = sym_read_2; // 代替 hw_region[ADDR_2]
    ...
}
```

驱动中对这些全局变量符号化：
```c
#include <klee/klee.h>
#include "patched/ip.c"  // 直接 include patched 实现

extern unsigned char sym_read_1, sym_read_2;

void case_xx(void) {
    IP ip;
    // 初始化所有非符号化字段（参数、指针等）
    ip.param = SOME_VALUE;

    /* 符号化硬件读取值 */
    klee_make_symbolic(&sym_read_1, sizeof(sym_read_1), "read_1");
    klee_make_symbolic(&sym_read_2, sizeof(sym_read_2), "read_2");

    IP_Func(&ip);
    // 验证后置条件...
}
```

**方式二：直接符号化 patched 版本中的全局数组**

在 patched 实现中去掉 `volatile` 后，驱动可直接调用 `klee_make_symbolic` 符号化全局数组：
```c
#include "patched/ip.c"

void case_xx(void) {
    ip.param = SOME_VALUE;

    /* 直接符号化已去 volatile 的全局数组 */
    klee_make_symbolic(hw_region, sizeof(hw_region), "hw_region");
    klee_make_symbolic(&ctrl_reg, sizeof(ctrl_reg), "ctrl_reg");

    IP_Func(&ip);
    // 验证后置条件...
}
```

注意：方式二符号化整个数组（可能很大），KLEE 可能因内存过大而不可行。此时优先使用方式一，仅符号化实际被读取的地址。

无论使用哪种方式，都必须在验证报告中注明 patched 修改，并说明验证结论适用于等效的非 volatile 建模。

注释提示内容由 IP 源形式模型规约文档转换而来。若源文档存在错误，则注释提示内容也会跟着有错。
规约文档存在内容错误是 IP 设计中的潜在问题，应该由验证工作流来发现，当前阶段不要掩盖错误。

原则：必须严格按照注释提示转换代码，使得验证断言与文档中描述的性质完全一致

## 前后置断言

若注释给出的是合法的 C 语言表达式，则严格按照注释内容进行转换，
仅当表达式是主合取范式时可以拆分成多条断言，其余情况禁止转换表述。示例：
```c
// assume !(a == 0) && x > 0 && y > 0
// assert !(s > 0 || t != 0)

// 正例
klee_assume(!(a == 0));
klee_assume(x > 0);
klee_assume(y > 0);
klee_assert(!(s > 0 || t != 0));

// 反例：未严格按照注释提示补充断言。禁止转换表述，即使语义等价的转换也不允许
klee_assume(a != 0);
klee_assume(x > 0 && y > 0);
klee_assert(s <= 0);
klee_assert(t == 0);
```

使用注释中的变量名和常量值，不要替换。示例：
```c
// assert a == FALSE_ && b == 1
// 已知宏 FALSE_ 定义为 0，宏 TRUE_ 定义为 1
// 正例：使用断言中的变量名和值
klee_assert(a == FALSE_ && b == 1);
// 反例：禁止替换常量和字面量值
klee_assert(a == 0 && b == TRUE_);
```

若注释提示中的断言内容无法直接用 C 语言表达式表示，则根据实际情况进行合理转换，示例：
```c
// assert a == {0=x,1=y} && x > y > z
// 正例：转换成 C 语言表达式，尽量细化断言内容，拆分成多项
klee_assert(a[0] == x);
klee_assert(a[1] == y);
klee_assert(x > y);
klee_assert(y > z);
// 反例：未转换成 C 语言表达式，无法通过编译
klee_assert(a == {0=x,1=y} && x>y>z);
```

## 变量名转换

使用 IP 的成员变量名，示例：
```c
// assume a > BB

// 正例（若 a 是 IP 成员变量，BB 是常量枚举）
klee_assume(ip.a > BB);
// 反例
klee_assume(a > 1);
```

## 规约布尔→C整型

若 IP 实现用整型存储布尔值，使用 C 语义映射：`true` → 非零即真（`x`），`false` → 零为假（`!x`）。禁止硬编码与 0/1 比较，因为实现中可能使用非标准值（如 `TRUE32 = 0xEB90146F`）：
```c
// assert flag' == true
// 正例：使用 C 语义，非零为真
klee_assert(ip.flag, "flag' == true");
// 反例：禁止硬编码比较
klee_assert(ip.flag == 1, "flag' == true");
```

## 新旧值

`a` 和 `a'` 分别表示同一变量的旧值和新值。比较新旧值时，需新建变量 `old_xxx` 保存旧值。示例：
```c
// assert a' == a + 1

// 正例
int old_a = ip.a;
IP_Func(&ip);
klee_assert(ip.a == old_a + 1);

// 反例：未保存旧值
IP_Func(&ip);
klee_assert(ip.a == ip.a + 1);
```

## 数组、结构体、容器

`{x=s,y=t}` 字面量可能表示一个 C 数组或结构体，也可能表示抽象数据结构容器，示例：
```c
// assert a == {0=x,1=y}
// assert b == {s=x,t=y}
// assert c == {key=val}

// 根据实际代码进行转换，若 a 是数组，b 是结构体，c 是数据结构（容器），则转换成：
klee_assert(a[0] == x && a[1] == y);
klee_assert(b.s == x && b.t == y);
klee_assert(get(c, key) == val); // 根据容器 c 的定义，转换成正确的访问表达式
```

## 数组长度

形如 `len(a)` 和 `size(a)` 一类的函数，若 `a` 为 C 数组，转换成合适的获取长度的方式：

示例：
```c
// assume len(a) == N
// assert len(a') == M
// a 是已知长度的数组，struct IP { int a[n]; }; 则转换为：

// 正例
klee_assume(sizeof(ip.a) / sizeof(ip.a[0]) == N);
IP_Func(&ip);
klee_assert(sizeof(ip.a) / sizeof(ip.a[0]) == M, "...");
// 注意：上述判断并非冗余，即使编译期已知数组长度，也必须保留该判断
//   若规约文档内容没有笔误且代码实现满足规约，则有 N == n && M == n，

// 反例：错误使用代码声明中的数组长度 n，而非注释提示中的 N 和 M，无法正确表达验证意图
klee_assume(sizeof(ip.a) / sizeof(ip.a[0]) == n);
// 反例：未转换成获取数组长度的表达式
klee_assume(N == n && M == n);
// 反例：未正确转换成获取数组长度的表达式，直接使用注释中的 len(a) 表达式，无法通过编译
klee_assume(len(ip.a) == N);
// 反例：不要使用上下文推断的变量来判断长度
klee_assume(sizeof(ip.a) / sizeof(ip.a[0]) >= K);
```

```c
// assume len(a) == N
// assert len(a') == M
// a 是数组指针，struct IP { int *a; };

// 情况一：若无明确说明，优先使用栈内分配内存，转换为：
// 正例
int a[N];
klee_assume(sizeof(a) / sizeof(a[0]) == N); // 即使编译期已知长度，也保留该判断
ip.a = a;
IP_Func(&ip);
klee_assert(sizeof(a) / sizeof(a[0]) == M, "...");

// 反例：遗漏 assume，且未严格按照注释转换断言
int a[N];
ip.a = a;
klee_assert(N == M, "...");
// 反例：ip.a 是指针变量而非数组，sizeof 无法正确获取长度
klee_assert(sizeof(ip.a) / sizeof(ip.a[0]) == M, "...");

// 情况二：若已明确指出 a 是动态分配内存（例如指定使用 malloc），则转换为：
int *a = malloc(N * sizeof(int));
klee_assume(a != NULL);
IP_Func(&ip);
klee_assert(...);
// 判断动态申请的内存段的长度可能存在局限性，例如 IP 内部可能涉及 realloc()，此处未必能判断 len(a) == M
// 所以，除非明确说明，不要轻易使用动态内存分配。若 CBMC 无法检查，则明确指出该验证结果的局限性
```

示例：
```c
// assume size(a) == (3,2)

// 若 a 是二维数组，例如 struct IP { int a[3][2]; } 则转化成
klee_assume(sizeof(ip.a) / sizeof(ip.a[0]) == 3);
klee_assume(sizeof(ip.a[0]) / sizeof(ip.a[0][0]) == 2);
```

## 全称量词

模板中的全称量词 `forall` 优先考虑转换为符号化验证条件或有界展开来表达，示例：
```c
// forall ( var: i, range: from 0 to 9 step 1 ) { assert (a[i] == 0) }
// 注意：range from-to 的范围是前闭后开区间

// 正例：转换为符号化验证条件
int i;
klee_make_symbolic(&i, sizeof(i), "i");
klee_assume(0 <= i && i < 9);
klee_assert(a[i] == 0);

// 正例：显式展开固定小范围的全称量词
klee_assert(a[0] == 0);
klee_assert(a[1] == 0);
...
klee_assert(a[8] == 0);

// 正例：for 循环展开
for (int i = 0; i < 9; i++) {
    klee_assert(a[i] == 0);
}
```

注意：当量词范围依赖符号量（如 `[JoinTotal, N)` 中 `JoinTotal` 是符号量）时，若范围在某些路径下为空，`klee_assume` 的约束条件会变为不可满足，KLEE 报 `invalid klee_assume call (provably false)` 并生成 `*.user.err` 文件——这不是真实错误，而是正常的空范围情形。此时优先使用有界 for 循环 + if 条件代替 `klee_assume`，避免误报：
```c
// forall ( var: i, range: from JoinTotal to N ) { assert a[i] == 0 }
// JoinTotal 是符号量，范围可能为空

// 优先使用：for 循环 + if 条件（不产生 provably false）
for (int i = 0; i < N; i++) {
    if (i >= JoinTotal) {
        klee_assert(a[i] == 0);
    }
}
```

有些无界量词可能在实现中有隐含边界，将量词范围设置为一个合理的边界值。
真正无限域上的量词，可自行加边界，或指定 KLEE 的最大深度。
同时必须在最终验证结果报告中指出，只在边界内进行验证，不等价于完整数学规格

## 存在量词

由规约完全定义的见证变量，按规约直接构造见证值，再验证其余性质；
由规约部分定义的见证变量，已约束的分量直接赋值，未约束的分量用 `klee_make_symbolic` 填充，必要时添加 `klee_assume` 补充隐含约束。示例：
```c
// exists ( var: a; type: ℕ ) {
//   assert ...
// }

int a;
klee_make_symbolic(&a, sizeof(a), "a");
klee_assert(...);
```

若变量完全由 IP 计算产生，先调用 IP，再用符号变量 + assume 建模"存在一个满足性质的值"：
```c
// assume y...

IP_Func(&ip);
float y;
klee_make_symbolic(&y, sizeof(y), "y");
klee_assume(...);
klee_assert(...); // 判断 output 与 y 的关系
// 注意：该方式只能验证输出满足某种存在性条件，若无法得出结论，须在最终报告中说明局限性
```

若见证变量是 IP 内部不可观测的中间值（例如从 volatile 硬件寄存器读取并计算的 AD 转换结果），上述规则仍适用，但应注意：
- 在 patched 版本中去掉 volatile 后，硬件读取值变为可符号化，中间变量 wd 成为符号值的确定函数，其存在性自然成立
- 驱动应断言输出与中间变量的关系，而不是直接断言 wd 的取值
- 如果中间变量在 IP 内部且无法从外部观测，可在 patched 实现中将其暴露为全局变量或输出字段，再在驱动中引用
- 若无法暴露中间变量，可将输出值与规约给出的转换公式直接比较，但须在报告中说明该验证假设中间变量存在且符合规约

## 链式表达

提示中可能使用链式表达式，例如 `a > b > c`，需拆分成多条断言，示例：
```c
// assert a > b > c
// 正例
klee_assert(a > b && b > c, "a > b > c");
// 反例：在 C 语言中，a > b > c 会被解析为 (a > b) > c，无法正确表达断言语义
klee_assert(a > b > c, "a > b > c");
```

## 浮点数

KLEE 对浮点符号化的支持极其有限。KLEE 在内部会将浮点符号量并发化为 0，导致含浮点条件的 `klee_assume` 在多数情况下变为不可满足，
报 `invalid klee_assume call (provably false)`，且只能探索极少数路径。

对于以浮点为主要数据类型的 IP，不应尝试全符号化——这在 KLEE 中不可行。应优先采用具体典型值策略：
- 为输入端口选取代表性具体值（覆盖各分支条件的边界、典型场景），直接赋值，不用 `klee_make_symbolic`
- 每组典型值对应一个 case 或 _reduced 版本
- 在报告中说明：验证结论仅在所选典型值下成立，不等价于完整数学规格

示例：
```c
// IP 含浮点输入 x（规约要求 x > 0）

// 错误做法（KLEE 无法有效处理）：
float x;
klee_make_symbolic(&x, sizeof(x), "x");
klee_assume(x > 0.0f);   // provably false，几乎无路径可探索

// 正确做法（具体典型值）：
ip.x = 0.5f;   // 选取代表性正值
IP_Func(&ip);
klee_assert(...);
```

若 IP 仅部分字段涉及浮点，其余字段仍可符号化，对浮点字段单独选取典型值。

除非规约明确要求处理特殊值，否则排除 NaN/Inf 输入（对具体值直接使用正常浮点即可，无需额外 assume）。

浮点数的比较需根据场景选择不同策略，直接赋值精确比较，计算结果近似比较，示例：
```c
// 若 IP 输出是对输入直接赋值或转发，未经过浮点运算，则精确比较
klee_assert(ip.x == X && ip.y == 0.0f);
// 若 IP 输出是经过计算得到，则引入误差范围进行比较
#define EPSILON 1e-6f
klee_assert(fabsf(ip.z - (a * b)) < EPSILON);
```

## 浮点运算后置条件验证策略

当后置条件涉及浮点运算结果（如矩阵乘法、三角函数），即使输入使用具体典型值，KLEE 也无法自动验证计算结果的数学正确性。按以下优先级选择策略：

1. 计算预期结果并断言：若输入全部为具体值，且运算过程可手工或通过辅助函数推算出预期输出，则在驱动中直接计算预期值并断言比较。
   例如对具体矩阵乘法，可手写等价乘法函数计算预期 W 值，再与 IP 输出比较。此策略验证强度最高。
2. 误差范围近似比较：若运算过程包含浮点舍入或运算顺序差异，使用 `fabsf` + 误差范围比较。
   误差范围应根据 IP 实现的数值精度确定，避免过大掩盖实现错误。
3. 仅验证路径可达性与结构性质：若无法精确推算预期结果（如泛型矩阵乘法依赖外部库），则断言函数执行无 KLEE 错误（空性质 `assert(1)`），
   并在报告中说明：本 case 仅验证该路径下 IP 执行未触发运行时错误，浮点结果正确性需结合具体值 reduced-case 或人工审查确认。

无论使用哪种策略，均须在验证报告中说明验证覆盖范围（具体值集、路径分支等）和结论的局限性。

## 文本或 LaTeX

模板中的断言可能包含文本或 LaTeX 公式，需理解其语义，转换成等价的 C 代码表达式，必要时自定义辅助函数。

## 时序控制

`clock' = clock` 表示 IP 不涉及时序控制相关的行为，无需在代码中模拟时序逻辑，直接忽略该类注释即可

## 兜底规则

若出现上述规则以外的情况，可自行转换，并给出你的转换思路。
在最终验证报告上指出，当前规则转换提示词仍需完善

## SMT 性能提示

当规约使用 `x % pow(2, i+1) >= pow(2, i)` 形式表达"第 i 位为 1"的位检测时，SMT 求解器处理此类非线性模运算约束效率极低，容易引发路径爆炸。
可用等价的位运算 `(x >> i) & 1` 替换：语义完全相同，但 SMT 求解效率差异显著。
此类情形属于因建模性能问题而调整表达形式，不违反"严格按照注释提示转换"的原则，但需在报告中说明。
