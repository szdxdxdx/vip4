# LaTeX 规约文档结构化

---

## 输入：形式规约文档

软件 IP 形式模型规约文档用数学语言形式化描述了 IP 行为，由 LaTeX 编写，
编译成 pdf 后适合人类专家阅读，但 LaTeX 源码本身不适合由程序直接解析。

LaTeX 文档通常含以下章节：
* Variable Declaration  描述 IP 涉及的所有变量
  - Alphabet    IP 涉及的所有变量集合
  - Inputs      输入端口
  - Outputs     输出端口
  - In-Outputs  输入输出端口
  - States      状态变量
  - Parameters  配置参数
  - Clocks      时序相关
* AG Contract   描述 IP 的行为
  - Assumptions 前提
  - Guarantees  前置条件、后置条件

## 输出：JSON AST

按照下述规则，将文档的 LaTeX 内容进行结构化，转换为适合机器解析的 JSON 格式。
主要将 AG Contract 章节的内容转换成用 JSON 表达的 AST 结构，结果保存到 `<ir>/contract.json`

AST 的 JSON 格式如下：
```json
{
  "version": "0.0.8",
  "subchecks": { "<check_name>": <AST-node>, ... },
  "assumption": <AST-node>,
  "guarantee": <AST-node>
}
```
字段说明：
- `version` 填写当前 IR 的版本号。参照上述固定值，无特殊含义
- `subchecks` 规约的子检查项，键为检查项名称，值为 AST 节点
- `assumption` 前提条件的 AST 节点
- `guarantee` 整体规约的 AST 节点

错误处理：
若文档缺失必要的章节、文字内容混乱无法理解，或是内容与工作任务无关，则 AST 转换失败，应中止任务并汇报错误

## 原则

- 即使文档内容存在前后矛盾或逻辑错误，也严格依照原文内容进行转换，禁止擅自修改
- 文档内容上存在的逻辑错误也是 IP 设计中的潜在问题，应该由验证工作流来发现，当前阶段不要掩盖错误
- 严格使用文档中的变量名和字面量，不要替换
- 转换时，只参考 IP 的规约文档，不要参考 IP 的实际代码实现

## AST-node 转换规则

`<AST-node>` 节点的通用格式为 `{ "kind": <str>, ... }`

### 变量

变量转换为 `{"kind": "var", "name": <str>}`

`'` 表示同一变量不同时期的值，例如 `a` 为旧值，`a'` 为新值。该符号作为变量名的一部分，
示例：
```json
// a
{"kind": "var", "name": "a"}

// b'
// 正例
{"kind": "var", "name": "b'"}
// 反例：省略了时序后缀 '，丢失新旧值语义
{"kind": "var", "name": "b"}
```

LaTeX 中的 `{x→y}` 可以表示 C 原生数组或结构体，也可以表示抽象数据结构容器，例如：
- `a={0→x,1→y}` 可以表示数组或顺序容器 `a[0]=x` 和 `a[1]=y`
- `a={s→x,t→y}` 可以表示结构体或映射容器 `a.s=x` 和 `a.t=y`

成员变量、容器中元素访问操作，整体视作一个变量，示例：
```json
// x→y
{"kind": "var", "name": "x.y"}

// b.c[2].d
// 正例：整体作为一个 var 节点
{"kind": "var", "name": "b.c[2].d"}
// 反例：过度解析
{"kind": "access", "obj": {"kind": "var", "name": "b.c[2]"}, "field": "d"}
```

数组、结构体、容器在语义上都可以整体判断相等，无需在代码层面考虑逐一比对所有元素。

### 字面量

字面常量转换为 `{"kind": "val", "val": <str>, "type": <str>}`

`type` 可以是常见的数据类型或抽象的容器类型 `null|int|float|str|bool|array|map|set|...`，符合直觉即可，无需与实际代码一致
必要时才添加 `type` 字段来明确区分不同类型的字面量（例如字符串、无符号数等），否则可省略 `type` 字段

示例：
```json
// 3.14
{"kind": "val", "val": "3.14"}
// 0xff
{"kind": "val", "val": "0xff"}
// 数组、顺序容器 [x, y]
{"kind": "val", "type": "array", "val": "[x, y]"}
// 映射、结构体 {s→x, t→y}
{"kind": "val", "type": "map", "val": "{s: x, t: y}"}
// 集合、无序容器等
{"kind": "val", "type": "set", "val": "{a, b, c}"}
```

复杂数字、结构体对象、不含变量的数学运算式，都可以保留字面量形式，且内容可以稍做转换，示例：
```json
// {a→0xff, t→5.4*10^-6}
{"kind": "val", "val": "{a: 0xff, t: 5.4E-6}"}
```

### 运算符

以下运算在 C 语言中有内建运算符，转换成对应运算符节点。C 语言的内建运算符和对应的 `kind` 如下：
- 逻辑运算 `&& || !`
  `{"kind": "and|or|not", ...}`
- 比较运算 `<= >= < > == !=`
  `{"kind": "le|ge|lt|gt|eq|neq", ...}`
- 四则运算 `+ - * /`、取模 `%`、取反 `-`
  `{"kind": "add|sub|mul|div|mod|neg", ...}`
- 位运算
  `{"kind": "bit_and|bit_or|bit_xor|bit_shl|bit_shr|bit_not", ...}`
单目运算符转换为 `{"kind": ..., "arg": <AST-node>}`
双目运算符转换为 `{"kind": ..., "lhs": <AST-node>, "rhs": <AST-node>}`
示例：
```json
// x≥y ∧ (b≠0 ∨ ¬c）
{
  "kind": "and",
  "lhs": {"kind": "ge", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "var", "name": "y"}},
  "rhs": {
    "kind": "or",
    "lhs": {"kind": "neq", "lhs": {"kind": "var", "name": "b"}, "rhs": {"kind": "val", "val": "0"}},
    "rhs": {"kind": "not", "arg": {"kind": "var", "name": "c"}}
  }
}
```

部分运算节点允许链式表达形式，转换为 `{"kind": ..., "args": [<AST-node>, ...]}`
- 允许链式表达的节点： `and|or|le|ge|lt|gt|eq|add|mul`
- 相同运算符的链式表达（参数个数 >= 2），转换节点时也使用链式表达
- 不同运算符的链式表达，拆分成 `and` 节点的链式表达
示例：
```json
// x ∧ y ∧ z
// 正例，拆分成两个 and 节点
{"kind": "and", "lhs": <AST-node: x>, "rhs": {"kind": "and", "lhs": <AST-node: y>, "rhs": <AST-node: z> }}
// 正例（推荐），链式表达
{
  "kind": "and", "args": [
    {"kind": "var", "name": "x"}, {"kind": "var", "name": "y"}, {"kind": "var", "name": "z"}
  ]
}

// x=y>z>0
// 正例：不同运算符，禁止链式表达
{
  "kind": "and", "args": [
    {"kind": "eq", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "var", "name": "y"}},
    {"kind": "gt", "lhs": {"kind": "var", "name": "y"}, "rhs": {"kind": "var", "name": "z"}},
    {"kind": "gt", "lhs": {"kind": "var", "name": "z"}, "rhs": {"kind": "val", "val": "0"}}
  ]
}
```

---

LaTeX 文档中，`:=` 表示赋值，`=` 表示判断相等，`a:=0` 相当于 `a'=0`。`(a,b) := (x,y)` 形式的同时赋值。示例：
```json
// x=1
{"kind": "eq", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "val", "val": "1"}}

// y:=1
{"kind": "eq", "lhs": {"kind": "var", "name": "y'"}, "rhs": {"kind": "val", "val": "1"}}

// (a,b):=(s,t)
{"kind": "and", "args": [
  {"kind": "eq", "lhs": {"kind": "var", "name": "a'"}, "rhs": {"kind": "var", "name": "s"}},
  {"kind": "eq", "lhs": {"kind": "var", "name": "b'"}, "rhs": {"kind": "var", "name": "t"}}
]}
```

---

蕴含 `P⇒Q` 转换为 `{"kind": "implies", ...}`，示例：
```json
// P ⇒ Q
// 正例
{"kind": "implies", "lhs": <AST-node: P>, "rhs": <AST-node: Q>}
```

---

其余运算符转换成函数调用，或者转换成文本形式，详见下文。

### 函数调用

函数调用转换为 `{"kind": "call", "fn": <str>, "args": [<AST-node>,...], "kwargs": {<str>: <AST-node>, ...}}`，
无参数时 `args` 和 `kwargs` 可省略。示例：
```json
// f()
// g(x=2)
// h(a, b)
{"kind": "call", "fn": "f"}
{"kind": "call", "fn": "g", "kwargs": {"x": {"kind": "val", "val": "2"}}}
{"kind": "call", "fn": "h", "args": [{"kind": "var", "name": "a"}, {"kind": "var", "name": "b"}],}
```

### 数学运算

文档中显式命名的数学函数，转换成函数调用，且保留文档中的函数名，不替换。示例：
```json
// \min{a,b}
// \sqrt{y}
// 正例
{"kind": "call", "fn": "min", "args": [{"kind": "var", "name": "a"}, {"kind": "var", "name": "b"}]}
{"kind": "call", "fn": "sqrt", "args": [{"kind": "var", "name": "y"}]}
// 反例：未使用文档中的函数名 min，而是擅自猜测代码中的实际函数名
{"kind": "call", "fn": "fmin", ...}
```

文档中出现的数学符号，若在 C 语言中没有对应的内建运算符，则转换为最接近的 C 标准库函数名。
只考虑数学符号的语义，选择最贴合语义的、最精简的 C 标准库函数名，不用考虑代码中参数的实际类型。
示例：
```json
// |x|  绝对值
// |y|  模长、序列长度（同一数学符号有多种不同用法，需根据上下文推断其实际含义）
// ⌊z⌋  向下取整
// a^b  幂运算（若无明确位运算场景，^ 符号理解成幂运算）
// 正例
{"kind": "call", "fn": "abs", "args": [{"kind": "var", "name": "x"}]}
{"kind": "call", "fn": "len", "args": [{"kind": "var", "name": "y"}]}
{"kind": "call", "fn": "floor", "args": [{"kind": "var", "name": "z"}]}
{"kind": "call", "fn": "pow", "args": [{"kind": "var", "name": "a"}, {"kind": "var", "name": "b"}]}
```

十分复杂的数学运算，转换成文本形式，语义描述准确即可，不要求与实际代码完全一致。示例：
```json
// ∑a[i]
// \max{ b[i] | i ∈ [0,N) }
// 正例
{"kind": "call", "fn": "sum", "args": [{"kind": "text", "text": "a[i] for each i"}]}
{"kind": "call", "fn": "max", "args": [{"kind": "text", "text": "b[i] for i in [0,N)"}]}
// 正例
{"kind": "text", "text": "the sum of a[i] for each i"}
{"kind": "text", "text": "the max of a[i] for i in [0,N)"}

// A×B  矩阵乘法（根据上下文推断）
// 正例
{"kind": "call", "fn": "matrix_multiply", "args": [{"kind": "var", "name": "A"}, {"kind": "var", "name": "B"}]}
// 正例，但不推荐
{"kind": "text", "text": "the product of matrix A and matrix B"}
{"kind": "text", "text": "A×B"}

// |x|
// 正例，但不推荐
{"kind": "text", "text": "|x|"}
```

### 分支

if-else 分支结构转换为 `{"kind": "if", "cond": <AST-node>, "then": <AST-node>, "else": <AST-node>}`
分支的写法形式不唯一，示例：
```json
// if C then P else Q endif
// P ⊲ C ⊳ Q
{"kind": "if", "cond": <AST-node: C>, "then": <AST-node: P>, "else": <AST-node: Q>}
```

留心：多层 if 嵌套时，LaTeX 代码使用空格或对齐命令来表达缩进层级关系。

### 量词

`∀x∈D·P` 和 `∃x∈D·P` 转换为
```json
{
  "kind": "forall|exists",
  "vars":[{"name": <str>, "type": <str>, "range": <str>},...],
  "body": <AST-node>
}
```
其中：
- `vars.[].type` 为变量论域，优先采用数学符号，例如数集 `ℤ|ℕ|ℝ`、函数空间 `A→B` 等；
  其次考虑使用代码类型（符合直觉即可，无需与实际代码一致），例如 `number|string|bool|a->b|...` 等
  若上下文不足，推断不出类型，则省略 `type` 字段
- `vars.[].range` 为量词的辖域限定，若上下文信息不足，则省略 `range` 字段
- `body` 是该组变量绑定作用域内的完整 AST

示例：
```json
// ∀i∈[0, size) P(i)
{"kind": "forall", "vars": [{"name": "i", "type": "ℕ", "range": "0 <= i < size"}], "body": <AST-node: P(i)>}

// ∀0≤i≤k ∀i≤j≤k P(i,j)
{
  "kind": "forall", "vars": [
    {"name": "i", "type": "ℕ", "range": "0 <= i <= k"},
    {"name": "j", "type": "ℕ", "range": "i <= j <= k"}
  ],
  "body": <AST-node: P(i)>
}

// ∀item∈container P(item)
{"kind": "forall", "vars": [{"name": "item", "range": "for each item in container"}], "body": <AST-node: P(item)>}

// ∃x,y∈ℕ P(x,y)
{"kind": "exists", "vars": [{"name": "x", "type": "ℕ"}, {"name": "y", "type": "ℕ"}], "body": <AST-node: P(x,y)>}
```

### 子检查项

将文档中除了 Assumption 和 Guarantee 之外的规约项，提取到 JSON 根节点的 `subchecks` 字段中，
例如 `Check1 ≜ ...` 提取成 `"subchecks": { "Check1": <AST-node> }`
若无，则 `subchecks` 字段为空 `{}`

引用的规约项转换为 `{"kind": "subcheck", "name": <check-name>}`

subcheck 中自由出现的量词变量，其绑定关系由调用处决定，转换时直接保留即可，作用域的语义信息交由后续工作流节点处理。

示例：
```json
// Check1 ≜ a>0
// Check2 ≜ x<10
// Guarantee: Check1 ∧ ∃x∈ℕ( Check2 )

// 正例
{
  "subchecks": {
    "Check1": {"kind": "gt", "lhs": {"kind": "var", "name": "a"}, "rhs": {"kind": "val", "val": "0"}},
    "Check2": {"kind": "lt", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "val", "val": "10"}}
  },
  "guarantee": {
    "kind": "and",
    "lhs": {"kind": "subcheck", "name": "Check1"},
    "rhs": {
      "kind": "exists", "vars": [{"name": "x", "type": "ℕ"}], "body": {"kind": "subcheck", "name": "Check2"}
    }
  }
}

// 反例：不要将 subcheck 的内容内联展开
{
  "guarantee": {
    "kind": "and",
    "lhs": {"kind": "gt", "lhs": {"kind": "var", "name": "a"}, "rhs": {"kind": "val", "val": "0"}},
    "rhs": {
      "kind": "exists", "vars": [{"name": "x", "type": "ℕ"}],
      "body": {"kind": "lt", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "val", "val": "10"}}
    }
  }
}
```

### 兜底规则

若能理解规约项内容，但无法匹配以上任何一条转换规则，则转换为 `{"kind": "text", "text": <str>}`，
其中 `text` 是单行文本，用自然语言或结构化语言来描述或总结规约项内容。可以表达复杂的数学式，或是描述复杂过程等。

若无法确定规约项内容，转换为 `{"kind": "latex", "text": <str>}`，忠实保留 LaTeX 原文。

只能容忍小部分复杂内容转换成文本或 LaTeX，禁止大范围使用该兜底规则，否则将丢失过多的结构化信息，降低后续验证流程的效果。
示例：
```json
// a>0 ∧ b>0

// 反例：存在对应的结构化节点，不应使用兜底规则
{"kind": "text", "text": "a > 0 and b > 0"}
```

```json
// ∑_{i=0}^{N} f(a[i],b[i]) > M

// 正例：只将复杂的求和表达式转换成文本，保留 gt 运算符的结构
{
  "kind": "gt",
  "lhs": {"kind": "text", "text": "sum(f(a[i], b[i]) for i from 0 to N)"},
  "rhs": {"kind": "var", "name": "M"}
}
// 反例：整体用 text 掩盖结构
{"kind": "text", "text": "the sum of f(a[i],b[i]) must be greater than threshold"}
```

## 其他补充说明

布尔变量作为独立合取项，示例：
```json
// a ∧ x=1
{
  "kind": "and",
  "lhs": {"kind": "var", "name": "a"},
  "rhs": {"kind": "eq", "lhs": {"kind": "var", "name": "x"}, "rhs": {"kind": "val", "val": "1"}}
}
```

---

链式表达的操作数可以是任意类型的节点，示例：
```json
// a=1=f(b) ∧ Check1 ∧ "some complex condition"
{
  "kind": "and", "args": [
    {
      "kind": "eq", 
      "lhs": {"kind": "var", "name": "a"},
      "rhs": {
        "kind": "eq",
        "lhs": {"kind": "val", "val": "1"},
        "rhs": {"kind": "call", "fn": "f", "args": [{"kind": "var", "name": "b"}]}
      }
    },
    {"kind": "subcheck", "name": "Check1"},
    {"kind": "text", "text": "some complex condition"}
  ]
}
```

---

不支持顺序节点 `seq`。当规约项包含顺序语义时，若各规约项直接无关联，则丢失顺序语义，尝试转换成 `and` 节点；
否则使用 `text` 节点，再不行直接中止转换，汇报错误提示当前工作流不支持处理这类规约。
