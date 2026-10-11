# 执行 CPAchecker 验证

## 创建验证配置

CPAchecker 的验证配置 `<case_name>.json` 示例如下：
```json
{
  "splited_from": <null|str>,
  "reduced_from": <null|str>,
  "py_subprocess": {
    "timeout": <int>
  },
  "cpachecker": {
    "files": [<str>],
    "options": {
      "-config": <str>,
      "-spec": <str>,
      "-entryfunction": <str>,
      "-I": [<str>],
      "-D": [<str>],
      "-setprop": {
        "<property.name>": <str|number|bool>
      }
    }
  },
  "docker": {
    "image": <str>,
    "arguments": [<str>]
  }
}
```

字段说明：
- `cpachecker` CPAchecker 配置项，最终转换为容器内的 `cpachecker [options] files...`
- `cpachecker.files` 填写所有参与验证的 C 文件路径
    包含 IP 源文件（直接使用原始文件路径）、依赖实现文件或桩文件，以及验证驱动 `<case_name>.c`，只填写最小必要集合
    路径可为绝对路径，也可相对套件目录；外部文件所在目录会只读挂载到容器，套件目录挂载到 `/work`
- `cpachecker.options` 填写 CPAchecker 支持的参数
    开放结构，普通 string / number 以 key-val 形式加入命令，array 重复展开每项，bool true 以 flag 形式加入命令，bool false 不加入命令
- `cpachecker.options.-I` 填写头文件搜索路径
- `cpachecker.options.-D` 填写预处理宏定义；根据待验证源码的编译环境补充，不得把特定项目宏固定到工作流中
- `cpachecker.options.-config` 填写分析配置。标准相对名称会映射到镜像内 `/cpachecker/config/`，其他镜像布局应填写经检查确认的容器内绝对路径
- `cpachecker.options.-spec` 填写 specification。标准相对名称会映射到镜像内 `/cpachecker/config/specification/`，不得臆造不存在的路径
- `cpachecker.options.-entryfunction` 填写验证入口函数，即验证驱动中的 case 函数名
- `cpachecker.options.-setprop` 填写 CPAchecker Java property，逐项转换为 `--option property=value`；布尔值转换为小写 `true` / `false`
- `docker.image` 填写本地可用的 CPAchecker 镜像，不得在驱动或脚本中固定镜像
- `docker.arguments` 填写额外的 `docker run` 参数；无则为空数组，不要重复添加脚本自动生成的挂载和用户参数

若无明确要求，功能性 case 优先使用 BMC 配置和断言 specification。BMC 适合快速发现反例和验证有明确上界的循环；循环界必须覆盖最长执行路径，并启用循环边界检查。
`cpa.loopbound.maxLoopIterations` 控制本次分析采用的实际循环界，`cpa.loopbound.maxLoopIterationsUpperBound` 只限制自动增大界的上限，不能代替前者。
读取 `Statistics.txt` 核对 `Bound k`、实际最大循环迭代和边界到达情况；即使结果为 FALSE，也要排除失败目标来自循环展开不足。

Java property 的名称、类型和语义可能随 CPAchecker 版本变化。
加入 `-setprop` 前应查看镜像内对应配置、帮助或实际启动日志确认，不能根据其他版本假设布尔或整数类型；
配置解析失败属于配置错误，应删除或改正该 property 后重跑。

当 BMC 难以证明含循环不变量或复杂整数控制流的性质时，可尝试 predicate analysis。切换分析策略前应确认镜像内配置文件存在，
并检查当前驱动、入口、断言 specification 和预处理配置正确，避免把建模错误误判为分析能力不足。

非功能性验证按性质拆分 case 和配置，避免不同目标相互干扰：
- 内存安全使用镜像内经确认的 memory-safety 配置及对应 specification，检查无效解引用、越界访问和其他内存错误；
  默认配置超时时，可尝试同版本提供的 SV-COMP memory-safety 配置
- 整数溢出使用镜像内经确认的 overflow 配置及对应 specification；predicate overflow 配置在浮点程序上因求解器能力返回 UNKNOWN 时，
  可尝试同版本提供的 BMC overflow 配置，并核对循环界

具体配置名称和支持的 property 取决于镜像中的 CPAchecker 版本，应通过容器内帮助信息和 `config/` 内容确认，不使用未经确认的名称。

## 执行验证

使用 `<skill>/scripts/cpachecker/run_cpachecker.py` 执行验证
脚本将简要打印 CPAchecker 执行结果，完整结果将保存（覆盖写入）到 `<suite>/output/cpachecker/<case_name>/` 目录：
- `cpachecker_stdout.txt` CPAchecker stdout
- `cpachecker_stderr.txt` CPAchecker stderr
- `cpachecker_output/`    CPAchecker 产物目录
- `result.json`

查看 `cpachecker_stdout.txt` 的最终结果行、`cpachecker_stderr.txt` 的 warning/error，以及 `Statistics.txt` 的停止原因和资源指标；
FALSE 时检查 assignment、counterexample、violation 或 witness 文件。FALSE case 应确保 CPAchecker 生成可机械解析的文本反例路径；
若当前配置只生成图、witness 或工具 HTML，应优先调整输出选项或分析配置补充文本路径。
无法获得文本路径时不得伪造，必须在最终报告标记反例路径缺失。不要仅凭进程退出码判定性质。

## 验证策略调整规则

先校正入口、specification、预处理、输入约束和循环界，再调整 timeout、BMC/predicate 等分析配置；
可显式展开固定小循环或数组下标。仅增加资源、切换已确认健全且语义等价的配置或修正错误时覆盖重跑原 case；
降低循环界、固定输入、限制下标、删除部分断言或采用非等价模型时必须创建 reduced-case，并记录具体 relation。
环境、权限、模型或不可恢复构建错误应立即中止，不得通过派生 case 绕过。

## 验证策略调整指导和错误处理

运行日志若警告 specification 未监视断言目标函数，本次结果不可用，必须修正断言与 specification。
若 specification 已明确监视该函数，但某个分析 CPA 仍警告未知函数返回值、忽略副作用或可能不可靠，不要与“未监视断言”混为一谈；
应结合所用 CPA 和结果路径判断可信度，并在 case 分析中披露该 soundness warning。

### 验证超时或 UNKNOWN

先检查入口、断言 specification、循环界、输入域和配置是否正确，再调整时间限制或分析策略。
BMC 因状态空间过大无法推进时，可等价拆分断言、显式展开固定小范围驱动循环，或尝试 predicate analysis；
memory-safety 分析可在不削弱性质的前提下选择镜像内其他可信配置。

仅在完整目标仍无法执行时创建 reduced-case。所有范围缩减、固定输入、代表性下标和模型替换都必须在报告中注明，缩减结果不能覆盖父 case 的 UNKNOWN 或 TIMEOUT。
