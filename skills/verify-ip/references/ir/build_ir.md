# IR 构建

将待验证 IP 内容转换为 SKILL 内部的中间过程表示 IR

## IR 目录结构

```
<verify_ip_workspace>/
|   ir/
|   |   ip.json          # 待验证 IP 基本信息
|   |   cases_tmpl.c     # 全部待验证性质（模板）
|   |   contract.json    # 由 LaTeX 格式的形式模型转换而来的 JSON AST
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
`ip` 填写待验证 IP 的名称。

### step-2 转换形式模型

将形式模型转换成待验证的性质模板 `cases_tmpl.c`。根据实际形式模型的内容格式，选择合适的转换方式：

- 如果形式模型是 LaTeX 文档，用数学公式描述 IP 的行为，
  1. 根据 `<skill>/references/ir/latex_to_json_ast.md`，
     将 LaTeX 文档转换为 JSON AST，生成 `contract.json`，
  2. 使用 `<skill>/scripts/ir/make_cases_tmpl.py` 生成 `cases_tmpl.c`
     参数 `--ir <ir>` 指定 IR 目录

- 如果形式模型不是 LaTeX 文档，而是其他格式的文档，
  根据 `<skill>/references/ir/other_format_to_cases_tmpl.md`，
  直接理解全部形式模型并生成 `cases_tmpl.c`，不创建或依赖 `contract.json`。

### step-3 检查 IR

使用 `<skill>/scripts/ir/check_ir.py` 检查 IR 格式是否有误
参数 `--ir <ir>` 指定 IR 目录
脚本将同时检查上述步骤提到的所有产物，结果输出到 stdout，不用保存到文件中。

## 异常处理

一旦 IR 构建或整个 IR 检查中任何步骤出现异常，则中止 IR 构建，并记录异常信息到 `error_report.md` 中
- 重点记录因 IP 内容本身导致的、与 IR 构建相关的异常信息
- 也可记录 SKILL 本身指导不明确或有误导致的异常信息
- 只汇报 IR 构建过程中的、已出现的状况，不要猜测可能出现的异常或问题
