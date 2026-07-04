---
name: code-review
description: 代码审查辅助
version: 1.0.0
type: skill
tools: [Read, Grep, Glob, Bash]
---

# Code Review

对 Pull Request 的代码变更进行审查，输出结构化审查意见。

## 步骤

1. 获取 PR 信息：`git log --oneline`
2. 阅读变更文件
3. 检查常见问题
4. 输出审查报告
