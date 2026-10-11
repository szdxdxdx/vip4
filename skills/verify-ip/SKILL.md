---
name: verify-ip
description: 对软件 IP 进行形式化验证
---

## SKILL 介绍

本 SKILL 面向软件 IP 的自动化形式化验证

用户提供待验证的 IP 并指定验证工具，由 AI Agent 自动调用工具来对 IP 进行形式化验证，并生成验证结果报告

目标：验证 IP 的实现是否满足其形式模型中描述的行为规范
输入：待验证 IP、指定使用的验证工具
输出：验证套件，含验证驱动代码、验证工具配置、验证工具输出、最终的验证结果报告等内容

当前 SKILL 支持的验证工具：
- CBMC
- KLEE
- CPAChecker

## 何时执行 SKILL

当且仅当用户明确指出【使用本 SKILL】对某个软件 IP 进行形式化验证时，才执行 SKILL

## 如何执行 SKILL

详见 `<skill>/references/workflow.md`
