
# 软件 IP 验证

## 软件 IP 背景介绍

软件 IP 是一类可复用的 C 语言程序模块，其头文件代码遵循以下格式内容：
```c
// 一个 IP 对应一个核心结构体，该结构体封装了该模块实例所需的所有数据
typedef struct IP {
    fn     // 指向绑定的核心功能函数
    input  // 输入端口
    output // 输出端口
    inout  // 输入输出端口
    state  // 状态变量，跨多次执行持久存在，内部数据
    param  // 配置参数，常量
} IP;

void IP_Func(void *p); // 核心功能函数
```

一个软件 IP 至少包含：
- 形式模型：用形式化数学语言描述的、用 LaTeX 编写的 IP 行为文档
- 实现：包含 .h 和 .c 文件的源码实现

## SKILL 目录结构

```
<skill>/              # 表示当前 SKILL 所在目录
|   doc/              # 开发和使用文档，供用户浏览，Agent 无需查看
|   core/             # SKILL 内部代码，Agent 无需查看
|   references/       # SKILL 文档，供 Agent 翻阅
|   scripts/          # 可直接执行的脚本，供 Agent 使用
|   .venv/            # 运行 SKILL 所需的 python 环境
|   requirements.txt  # python 环境依赖
|   SKILL.md
```

## 软件 IP 验证的工作目录结构

```
<verify_ip_workspace>/  # 本次 IP 验证的工作目录，由用户指定
|   ir/                 # 存放 IR 文件的目录
|   cbmc_suite/         # CBMC 验证工作目录
|   cpachecker_suite/   # CPAchecker 验证工作目录
|   klee_suite/         # KLEE 验证工作目录
|   tmp/                # 存放临时文件
```

## 软件 IP 验证工作流

### step-1 确定验证目标

确保用户已明确指出:
- 本次验证的工作目录 `<verify_ip_workspace>`
- 待验证的 IP
- 给出明确的验证任务

用户给出的任务可以是：
- 根据 IP 生成 IR
- 根据已有的 IR，指定验证工具，执行验证工作流
- 执行完整的验证工作流
若用户给出的任务不明确，或超出上述范围，则不执行验证任务

检查：
- 确保 IP 相关文件完整，包含形式模型和代码
- 工作目录最好是不存在（待创建的新目录）或是空目录，否则不应含有干扰本次验证任务的文件
- 必须指定 SKILL 所支持的验证工具之一

### step-2 准备环境

SKILL 所需的 python 虚拟环境位于 `<skill>/.venv/`
若虚拟环境不存在则创建，要求 python>=3.14（例如使用 `python3.14 -m venv`），并安装依赖 `<skill>/requirements.txt`
必须使用虚拟环境中的解释器来执行 `<skill>/scripts/` 中的 python 脚本

根据用户指定的验证工具，检查系统当前是否有可用的验证工具环境（只做轻量级检查，SKILL 不提供验证工具的安装配置指导）
- CBMC
    要求系统当前有可用的 CBMC，版本 CBMC>=6.8.0
- CPAchecker
    要求系统可执行 Docker，本地有可用的 CPAchecker 镜像
- KLEE
    要求系统当前有可用的 clang 和 klee 且 clang 生成的 LLVM bitcode 与 KLEE 所支持的 LLVM 版本兼容
    建议 KLEE>=3.2，clang 使用 /usr/bin/clang-13

### step-3 转换中间过程表示 IR

将待验证 IP 相关内容转换为 SKILL 内部的中间过程表示 IR，结果保存到 `<verify_ip_workspace>/ir/`
转换规则详见：`<skill>/references/ir/build_ir.md`

IR 能兼容不同的验证工具后端
若 `<verify_ip_workspace>/ir/` 目录已存在，或用户明确指定复用外部已生成的 IR，则跳过当前步骤

### step-4 执行 IP 验证

详见 `<skill>/references/ip/verify_ip.md`

---

## 要求

除非用户明确指出，否则不允许借鉴、查阅其他历史验证套件中的的任何内容。每一次验证都要独立

填写文件路径时（脚本参数、配置文件参数等）使用绝对路径

所有输出内容的主语言为【中文】，包括但不限于：代码注释、问题描述、结论说明等
