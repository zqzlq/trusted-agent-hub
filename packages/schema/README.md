# Schema 统一数据契约

本目录包含 Trusted Agent Hub 平台所有模块共享的 JSON Schema 定义。

## 文件

| 文件 | 说明 | 使用者 |
|------|------|--------|
| `agent-package.schema.json` | 统一能力包元数据 Schema | Web 提交表单、API 校验、CLI 渲染、扫描器输入 |
| `scan-report.schema.json` | 自动扫描报告 Schema | 扫描器输出、审核页渲染、评分模型输入 |
| `trust-score.schema.json` | 信任评分结果 Schema | 评分模型输出、Web 详情页、CLI 安装提示 |

## 示例

`examples/` 目录包含 4 个典型能力包的元数据示例：

- `skill-basic.json` — 高可信 Skill（代码审查）
- `mcp-server-basic.json` — 中可信 MCP Server（PostgreSQL 数据库）
- `plugin-basic.json` — 高可信 Plugin（开发者工具箱）
- `risky-skill.json` — 高风险 Skill（供扫描测试）

## 校验

```bash
# 安装 ajv-cli
npm install -g ajv-cli

# 校验示例文件
ajv validate -s agent-package.schema.json -d examples/skill-basic.json
ajv validate -s agent-package.schema.json -d examples/mcp-server-basic.json
ajv validate -s agent-package.schema.json -d examples/plugin-basic.json
ajv validate -s agent-package.schema.json -d examples/risky-skill.json
```

## 版本

- 当前版本：v0.1
- 冻结时间：第 2 周中
- 变更策略：字段新增向后兼容，废弃字段保留至少一个版本过渡期
