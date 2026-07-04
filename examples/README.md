# 能力包示例目录

本目录包含各种类型的能力包示例，供测试、演示和扫描器调优使用。

## 目录结构

```
examples/
├── skills/
│   └── demo-code-review/       # 代码审查 Skill 示例（高可信）
├── mcp-servers/
│   └── demo-filesystem/        # 文件系统 MCP Server 示例（中可信）
├── plugins/
│   └── demo-dev-toolkit/       # 开发者工具箱 Plugin 示例（高可信）
└── risky-packages/
    └── risky-executor/         # 风险执行器示例（高风险，仅供扫描测试）
```

## 示例分类

| 示例 | 类型 | 信任等级 | 用途 |
|------|------|---------|------|
| `demo-code-review` | Skill | 高可信 ✅ | 演示正常的 Skill 结构 |
| `demo-filesystem` | MCP Server | 中可信 ⚠️ | 演示 MCP Server，有文件读取权限 |
| `demo-dev-toolkit` | Plugin | 高可信 ✅ | 演示复合插件结构 |
| `risky-executor` | Skill | 高风险 ❌ | 演示包含多种安全风险的包，供扫描器测试 |

## 元数据文件

每个示例包在 `packages/schema/examples/` 下都有对应的元数据 JSON 文件，可用于：

- 验证 `agent-package.schema.json` 的正确性
- 作为 CLI 安装测试的 mock 数据
- 作为 Web 前端开发的展示数据

## 使用方式

### 本地开发测试

```bash
# 验证 Schema
npx ajv validate -s packages/schema/agent-package.schema.json \
  -d packages/schema/examples/skill-basic.json

# 查看示例包内容
cat examples/skills/demo-code-review/SKILL.md
```

### 扫描器测试

```bash
# 用 risky-executor 测试扫描规则
python scanners/risk-scanner/scan.py examples/risky-packages/risky-executor/

# 预期结果：应发现 10+ 个风险项
```
