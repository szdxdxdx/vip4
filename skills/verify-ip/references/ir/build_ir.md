# IR 构建

将待验证 IP 内容转换为 SKILL 内部的中间过程表示 IR

## IR 目录结构

```
<verify_ip_workspace>/
|   ir/                  # IR 存放目录
|   |   ip.json          # 记录待验证 IP 的基本信息
|   |   contract.json    # 前后置断言，描述 IP 的行为约束
|   |   error_report.md  # 当 IR 构建失败时，生成的错误报告
|   tmp/
```

## 构建步骤

### step-1 记录 IP 的基本信息

创建 `ip.json`，记录待验证 IP 的基本信息：
```json
{
  "ip": <str>
}
```
字段说明：
- `ip` 填写待验证 IP 的名称

### step-2 结构化形式规约

软件 IP 形式模型规约文档用数学语言形式化描述了 IP 行为，由 LaTeX 编写，编译生成的 PDF 便于人类专家阅读，
但文档内容缺乏统一的标准化格式要求，无法通过常规脚本进行自动化解析。
因此，需要将 LaTeX 内容进行结构化，转换为适合机器解析的 JSON 格式，该步骤只能依赖人工理解分析，
详见 `<skill>/references/ir/json_ast.md`

### step-3 检查 IR

使用 `<skill>/scripts/ir/check_ir.py` 检查 IR 格式是否有误
参数 `--ir <ir>` 指定 IR 目录
脚本将同时检查上述步骤提到的所有产物，结果输出到 stdout

## 异常处理

一旦 IR 构建或整个 IR 检查中任何步骤出现异常，则中止 IR 构建，并记录异常信息到 `error_report.md` 中
- 重点记录因 IP 内容本身导致的、与 IR 构建相关的异常信息
- 也可记录 SKILL 本身指导不明确或有误导致的异常信息
- 只汇报 IR 构建过程中的、已出现的状况，不要猜测可能出现的异常或问题
