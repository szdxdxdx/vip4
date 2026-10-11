
# 验证驱动编写指南

## 前后置断言

若注释给出的是合法的 C 语言表达式，则严格按照注释内容进行转换，
若表达式是主合取范式，推荐拆分成多条断言，其余情况禁止转换表述。示例：
```c
// assume !(a == 0) && x > 0 && y > 0

// 正例
__CPROVER_assume(!(a == 0));
__CPROVER_assume(x > 0);
__CPROVER_assume(y > 0);
```

使用注释中的变量名和常量值，不要替换。示例：
```c
// assert a == FALSE_ && b == 1
// 宏 FALSE_ 定义为 0，宏 TRUE_ 定义为 1

// 正例：使用断言中的变量名和值
__CPROVER_assert(a == FALSE_ && b == 1, "...");
// 反例：禁止替换常量和字面量值
__CPROVER_assert(a == 0 && b == TRUE_, "...");
```

若注释提示中的断言内容无法直接用 C 语言表达式表示，则根据实际情况进行合理转换，示例：
```c
// assert a == {0=x,1=y} && x > y > z
// 正例：转换成 C 语言表达式，尽量细化断言内容，拆分成多项
__CPROVER_assert(a[0] == x, "...");
__CPROVER_assert(a[1] == y, "...");
__CPROVER_assert(x > y, "...");
__CPROVER_assert(y > z, "...");
// 反例：未转换成 C 语言表达式，直接使用注释中的表述，无法通过编译
__CPROVER_assert(a == {0=x,1=y} && x>y>z, "...");
```

## 变量名转换

使用 IP 的成员变量名，示例：
```c
// assume a > 1
// a 是 IP 成员变量

// 正例
__CPROVER_assume(ip.a > 1);
// 反例
__CPROVER_assume(a > 1);
```

## 新旧值

`a` 和 `a'` 分别表示同一变量的旧值和新值。比较新旧值时，需新建变量 `old_xxx` 保存旧值。示例：
```c
// assert a' == a + 1

// 正例
int old_a = ip.a;
IP_Func(&ip);
int new_a = ip.a;
__CPROVER_assert(new_a == old_a + 1, "...");

// 反例：未保存旧值
IP_Func(&ip);
__CPROVER_assert(ip.a == ip.a + 1, "...");
```

## 数组、结构体、容器

`{x=s,y=t}` 字面量可能表示一个 C 数组或结构体，也可能表示抽象数据结构容器，示例：
```c
// assert a == {0: x, 1: y}
// assert b == {s: x, t: y}
// assert c == {key=val}

// 根据实际代码进行转换，若 a 是数组，b 是结构体，c 是数据结构（容器），则转换成：
__CPROVER_assert(a[0] == x && a[1] == y);
__CPROVER_assert(b.s == x && b.t == y);
__CPROVER_assert(get(c, key) == val); // 根据容器 c 的定义，转换成正确的访问表达式
```

## 数组长度

形如 `len(a)` 和 `size(a)` 一类的函数，若 `a` 为 C 数组，转换成合适的获取长度的方式

示例：
```c
// assume len(a) == N
// assert len(a') == M
// a 是已知长度的数组，struct IP { int a[n]; }; 则转换为：

// 正例
__CPROVER_assume(sizeof(ip.a) / sizeof(ip.a[0]) == N);
IP_Func(&ip);
__CPROVER_assert(sizeof(ip.a) / sizeof(ip.a[0]) == M, "...");
// 注意：上述判断并非冗余，即使编译期已知数组长度，也必须保留该判断
//   若规约文档内容没有笔误且代码实现满足规约，则有 N == n && M == n，

// 反例：错误使用代码声明中的数组长度 n，而非注释提示中的 N 和 M，无法正确表达验证意图
__CPROVER_assume(sizeof(ip.a) / sizeof(ip.a[0]) == n);
// 反例：未转换成获取数组长度的表达式
__CPROVER_assume(N == n && M == n);
// 反例：未正确转换成获取数组长度的表达式，直接使用注释中的 len(a) 表达式，无法通过编译
__CPROVER_assume(len(ip.a) == N);
// 反例：不要使用上下文推断的变量来判断长度
__CPROVER_assume(sizeof(ip.a) / sizeof(ip.a[0]) >= K);
```

```c
// assume len(a) == N
// assert len(a') == M
// a 是数组指针，struct IP { int *a; };

// 情况一：若无明确说明，优先使用栈内分配内存，转换为：
// 正例
int a[N];
__CPROVER_assume(sizeof(a) / sizeof(a[0]) == N); // 即使编译期已知长度，也保留该判断
ip.a = a;
IP_Func(&ip);
__CPROVER_assert(sizeof(a) / sizeof(a[0]) == M, "...");

// 反例：遗漏 assume，且未严格按照注释转换断言
int a[N];
ip.a = a;
__CPROVER_assert(N == M, "...");
// 反例：ip.a 是指针变量而非数组，sizeof 无法正确获取长度
__CPROVER_assert(sizeof(ip.a) / sizeof(ip.a[0]) == M, "...");

// 情况二：若已明确指出 a 是动态分配内存（例如指定使用 malloc），则转换为：
int *a = malloc(N * sizeof(int));
__CPROVER_assume(a != NULL);
IP_Func(&ip);
__CPROVER_assert(...);
// 判断动态申请的内存段的长度可能存在局限性，例如 IP 内部可能涉及 realloc()，此处未必能判断 len(a) == M
// 所以，除非明确说明，不要轻易使用动态内存分配。若 CBMC 无法检查，则明确指出该验证结果的局限性
```

示例：
```c
// assume size(a) == (3,2)

// 若 a 是二维数组，例如 struct IP { int a[3][2]; } 则转化成
__CPROVER_assume(sizeof(ip.a) / sizeof(ip.a[0]) == 3);
__CPROVER_assume(sizeof(ip.a[0]) / sizeof(ip.a[0][0]) == 2);
```

## 全称量词

模板中的全称量词 `forall` 优先考虑转换为符号化验证条件或有界展开来表达，示例：
```c
// forall ( var: i, range: 0 <= i < 9 ) { assert (a[i] == 0) }

// 正例：转换为符号化验证条件
int i = nondet_int();
__CPROVER_assume(0 <= i && i < 9);
__CPROVER_assert(a[i] == 0);

// 正例：显式展开固定小范围的全称量词
__CPROVER_assert(a[0] == 0);
__CPROVER_assert(a[1] == 0);
...
__CPROVER_assert(a[8] == 0);

// 正确
for (int i = 0; i < 9; i++) {
    __CPROVER_assert(a[i] == 0);
}
```

有些无界量词可能在实现有隐含边界，例如数组长度固定，协议窗口大小有限等，将量词范围设置为一个合理的边界值
真正无限域上的量词，可尝试自行加边界，或是指定 CBMC 循环展开的最大迭代次数
同时必须在最终验证结果报告中指出，只在边界内进行验证，不等价于完整数学规格

当需要验证 IP 内部循环对所有元素执行后的性质时，应确保 assume 对所有 i 同时成立（使用循环或展开），而非仅约束单个符号下标

## 存在量词

先按变量角色确定量词语义。通常应保持符号化全称语义，而不是固定一个典型输入
只有规约和验证目标确实要求“存在某个输入”时才按可达性处理，并在报告中明确该结论不代表全输入功能正确性。

由规约唯一确定的中间见证，按输入和旧状态确定性构造，并验证其论域、全部定义关系和后续性质。
非唯一但有限可枚举的见证，优先显式展开候选并断言至少一个候选满足。
多个性质要求同一见证时必须保持见证一致。
IP 内部且不可观测、又无法健全构造或枚举的见证，可尝试缩减验证范围。

由规约完全定义的见证变量，按规约直接构造见证值，再验证其余性质；
由规约部分定义的见证变量，已约束的分量直接赋值，未约束的分量用 `nondet_xxx()` 填充，仅可用 `__CPROVER_assume()` 描述其合法候选域。
示例：
```c
// exists ( var: a; type: ℕ ) {
//   assert ...
// }

int a; // 直接构造
__CPROVER_assert(...);
```

若变量完全由 IP 计算产生，或是其内部生成结果，无法在调用前预先构造，
则先调用 IP，再用 nondet 变量 + assume 建模"存在一个满足性质的值"。示例：
```c
// assume y...

IP_Func(&ip);
float y = nondet_float();
__CPROVER_assume(...);
__CPROVER_assert(...); // 判断 output 与 y 的关系
// 注意：该方式只能验证输出满足某种存在性条件，若 CBMC 无法处理，须在最终报告中说明局限性
```

## 浮点数

除非规约明确要求处理特殊值，否则排除 NaN/Inf 输入。示例：
```c
// 正例
float x = nondet_float();
double y = nondet_double();
__CPROVER_assume(x == x && -3.4028235e38f < x && x < 3.4028235e38f);
__CPROVER_assume(y == y && -1.7976931348623157e308 < y && y < 1.7976931348623157e308);

// 反例：x-x==0.0f 会触发 CBMC 的 --nan-check 导致假阳性，禁止使用
__CPROVER_assume((x == x) && (x - x == 0.0f));
// 反例：__CPROVER_isfinite() 内置函数存在缺陷，不要使用
__CPROVER_assume(__CPROVER_isfinite(x));
```

浮点数的比较需根据场景选择不同策略，直接赋值精确比较，计算结果近似比较，示例：
```c
// assert x' == X && y' == 0.0f
// assert z' == a * b

// 若 IP 输出 x 和 y 是对输入直接赋值或转发，未经过浮点运算，则精确比较，无需引入误差范围
__CPROVER_assert(ip.x == X && ip.y == 0.0f, "...");
// 若 IP 输出 z 是经过计算得到，则引入误差范围进行比较
#define EPSILON 1e-6f // 根据实际精度需求调整
__CPROVER_assert(fabsf(ip.z - (a * b)) < EPSILON, "..."); // 注意针对不同浮点类型选用不同的运算函数
```

若断言中的数学式与 IP 内部实现完全相同，且运算过程非常简单，则可尝试使用精确比较，以追求更强更精确的结论
但要注意，浮点计算可能因运算顺序不同而引入微小误差，精确比较断言可能会产生假失败，若失败则改回近似比较
示例：
```c
// assert z' == a * b + c

// 若 IP 内部也执行了相同的计算 z = a * b + c

// expected 既要正确表达断言中的数学式，其运算顺序、使用的中间变量等也要与 IP 内部实现完全一致
float expected = a * b + c;
IP_Func(&ip);
__CPROVER_assert(ip.z == expected, "z == a*b+c");  // 若断言出现假失败则改回近似比较
```

若因大量浮点符号化运算导致 SAT 求解超时：
- 可将参与大量浮点运算的配置参数固定为典型值，而非用 `nondet_float()` 全符号化
- 使用代表性单下标代替符号化下标，或拆分约束，减小验证范围
在最终验证结论中明确指出：仅在所选参数范围/下标范围内成立，不等价于完整数学规格

## 链式表达

提示中可能使用链式表达式，例如 `a > b > c`，需拆分成多条断言，示例：
```c
// assert a > b > c
// 正例
__CPROVER_assert(a > b && b > c, "...");
// 反例：在 C 语言中，a>b>c 会被解析为 a>b>c，无法正确表达断言语义
__CPROVER_assert(a > b > c, "...");
```

## 文本或 LaTeX

模板中的断言可能包含文本或 LaTeX 公式，需理解其语义，转换成等价的 C 代码表达式。示例：
```c
// assert M == min{ k | k such that sum(a[i] for i from 0 to k) == N }

// 可能需要自定义辅助函数，然后转换成如下形式：
__CPROVER_assert(M == find_min_k(...), "...");
```

## 时序控制

`clock' = clock` 表示 IP 不涉及时序控制相关的行为，无需在代码中模拟时序逻辑，直接忽略该类注释即可
