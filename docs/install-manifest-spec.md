# 安装 Manifest 格式规范

> 版本：v0.1  
> 冻结时间：第 2 周末  
> 负责人：B (Consumer 侧)  
> 关联文档：`packages/schema/agent-package.schema.json`

## 1. 设计目标

安装 Manifest 是 CLI 工具在安装能力包时从 Hub API 获取的核心数据。它比完整元数据 Schema 更精简，只包含安装过程必需的信息。CLI 在安装前必须展示 Manifest 中的风险信息，并在安装后将 Manifest 缓存到本地。

## 2. Manifest JSON Schema

### 2.1 顶层结构

```jsonc
{
  "$schema": "https://trusted-agent-hub.dev/schemas/install-manifest.schema.json",
  "manifest_version": "1.0",

  // 基本信息（来自 package + version）
  "name": "code-review-skill",
  "version": "1.0.0",
  "type": "skill",
  "description": "...",

  // 来源和校验
  "source": {},
  "integrity": {},

  // 安装指令
  "installation": {},

  // 权限和风险（CLI 安装前展示）
  "permissions": {},
  "risk_summary": {},
  "trust_score": 92,

  // 适配信息
  "compatibility": [],
  "dependencies": {}
}
```

### 2.2 完整 Schema 定义

```jsonc
{
  "type": "object",
  "required": [
    "manifest_version", "name", "version", "type",
    "source", "integrity", "installation",
    "permissions", "trust_score"
  ],
  "properties": {
    "manifest_version": {
      "type": "string",
      "const": "1.0"
    },
    "name": { "type": "string" },
    "version": { "type": "string" },
    "type": {
      "type": "string",
      "enum": ["skill", "mcp_server", "plugin", "subagent", "command", "prompt"]
    },
    "description": { "type": "string" },

    "source": {
      "type": "object",
      "required": ["type", "repository_url", "download_url"],
      "properties": {
        "type": { "type": "string" },
        "repository_url": { "type": "string", "format": "uri" },
        "download_url": {
          "type": "string",
          "format": "uri",
          "description": "包的下载地址（压缩包或 git archive URL）"
        },
        "ref": { "type": "string" },
        "commit_hash": { "type": "string" }
      }
    },

    "integrity": {
      "type": "object",
      "required": ["sha256"],
      "properties": {
        "sha256": {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$",
          "description": "下载内容的 SHA256 校验值"
        },
        "download_size_bytes": {
          "type": "integer",
          "description": "预估下载大小"
        }
      }
    },

    "installation": {
      "type": "object",
      "required": ["method", "steps"],
      "properties": {
        "method": {
          "type": "string",
          "enum": ["copy_directory", "npm_install", "pip_install", "docker_run", "manual_steps"]
        },
        "steps": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["action", "description"],
            "properties": {
              "action": {
                "type": "string",
                "enum": [
                  "download",
                  "extract",
                  "copy",
                  "npm_install",
                  "pip_install",
                  "docker_pull",
                  "write_config",
                  "run_script",
                  "verify"
                ]
              },
              "description": { "type": "string" },
              "source": { "type": "string" },
              "destination": { "type": "string" },
              "command": { "type": "string" },
              "config_template": { "type": "string" }
            }
          }
        },
        "target_client": { "type": "string" },
        "pre_install_message": { "type": "string" },
        "post_install_message": { "type": "string" }
      }
    },

    "permissions": {
      "type": "object",
      "properties": {
        "filesystem": {
          "type": "object",
          "properties": {
            "read": { "type": "array", "items": { "type": "string" } },
            "write": { "type": "array", "items": { "type": "string" } },
            "delete": { "type": "boolean" }
          }
        },
        "shell": {
          "type": "object",
          "properties": {
            "allowed": { "type": "boolean" },
            "commands": { "type": "array", "items": { "type": "string" } }
          }
        },
        "network": {
          "type": "object",
          "properties": {
            "allowed": { "type": "boolean" },
            "domains": { "type": "array", "items": { "type": "string" } }
          }
        },
        "environment": {
          "type": "object",
          "properties": {
            "read": { "type": "array", "items": { "type": "string" } },
            "write": { "type": "array", "items": { "type": "string" } }
          }
        },
        "credentials": {
          "type": "object",
          "properties": {
            "access": {
              "type": "array",
              "items": { "type": "string" }
            }
          }
        }
      }
    },

    "trust_score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100
    },

    "risk_summary": {
      "type": "object",
      "properties": {
        "level": {
          "type": "string",
          "enum": ["trusted", "low_risk", "medium_risk", "high_risk", "untrusted"]
        },
        "top_risks": {
          "type": "array",
          "items": { "type": "string" }
        },
        "install_recommendation": {
          "type": "string",
          "enum": ["safe", "review_recommended", "caution", "not_recommended", "blocked"]
        }
      }
    },

    "compatibility": {
      "type": "array",
      "items": { "type": "string" }
    },

    "dependencies": {
      "type": "object",
      "properties": {
        "system": { "type": "array", "items": { "type": "string" } },
        "npm": { "type": "array", "items": { "type": "object" } },
        "pip": { "type": "array", "items": { "type": "object" } }
      }
    }
  }
}
```

## 3. 示例 Manifest

### 3.1 Skill 安装 Manifest

```json
{
  "manifest_version": "1.0",
  "name": "code-review-skill",
  "version": "1.0.0",
  "type": "skill",
  "description": "对 Pull Request 执行多维度代码审查",
  "source": {
    "type": "github",
    "repository_url": "https://github.com/alice-dev/code-review-skill",
    "download_url": "https://github.com/alice-dev/code-review-skill/archive/refs/tags/v1.0.0.tar.gz",
    "ref": "v1.0.0",
    "commit_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
  },
  "integrity": {
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "download_size_bytes": 24576
  },
  "installation": {
    "method": "copy_directory",
    "steps": [
      {
        "action": "download",
        "description": "下载 v1.0.0 压缩包",
        "source": "https://github.com/alice-dev/code-review-skill/archive/refs/tags/v1.0.0.tar.gz"
      },
      {
        "action": "verify",
        "description": "校验 SHA256 完整性"
      },
      {
        "action": "extract",
        "description": "解压到临时目录"
      },
      {
        "action": "copy",
        "description": "复制到 Claude Code skills 目录",
        "destination": "~/.claude/skills/code-review-skill/"
      }
    ],
    "target_client": "claude-code",
    "post_install_message": "安装完成。使用 /review-pr 开始代码审查。"
  },
  "permissions": {
    "filesystem": { "read": ["./"], "write": ["./review-output/"], "delete": false },
    "shell": { "allowed": true, "commands": ["git", "diff", "grep"] },
    "network": { "allowed": false }
  },
  "trust_score": 92,
  "risk_summary": {
    "level": "trusted",
    "top_risks": [],
    "install_recommendation": "safe"
  },
  "compatibility": ["claude-code", "cursor"],
  "dependencies": { "system": ["git"] }
}
```

### 3.2 MCP Server 安装 Manifest

```json
{
  "manifest_version": "1.0",
  "name": "postgres-explorer",
  "version": "2.1.0",
  "type": "mcp_server",
  "description": "PostgreSQL 数据库只读浏览与查询",
  "source": {
    "type": "npm",
    "repository_url": "https://github.com/datatools-org/postgres-explorer",
    "download_url": "https://registry.npmjs.org/@datatools/postgres-explorer/-/postgres-explorer-2.1.0.tgz",
    "ref": "v2.1.0",
    "commit_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
  },
  "integrity": {
    "sha256": "d4c3b2a198fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b800",
    "download_size_bytes": 524288
  },
  "installation": {
    "method": "npm_install",
    "steps": [
      {
        "action": "npm_install",
        "description": "全局安装 @datatools/postgres-explorer",
        "command": "npm install -g @datatools/postgres-explorer@2.1.0"
      },
      {
        "action": "write_config",
        "description": "写入 Claude Code MCP 配置",
        "config_template": "{\n  \"mcpServers\": {\n    \"postgres-explorer\": {\n      \"command\": \"npx\",\n      \"args\": [\"@datatools/postgres-explorer@2.1.0\"],\n      \"env\": {\n        \"DATABASE_URL\": \"${DATABASE_URL}\"\n      }\n    }\n  }\n}"
      }
    ],
    "target_client": "claude-code",
    "pre_install_message": "此 MCP Server 需要访问 PostgreSQL。请确保已配置 DATABASE_URL。"
  },
  "permissions": {
    "filesystem": { "read": [], "write": [], "delete": false },
    "shell": { "allowed": false },
    "network": { "allowed": true, "domains": ["localhost"] }
  },
  "trust_score": 85,
  "risk_summary": {
    "level": "low_risk",
    "top_risks": ["需要访问本地 PostgreSQL 实例"],
    "install_recommendation": "safe"
  },
  "compatibility": ["claude-code", "mcp-client-generic", "cursor"],
  "dependencies": {
    "npm": [{ "name": "pg", "version": "^8.13.0" }],
    "system": ["node"]
  }
}
```

## 4. CLI 安装流程

```
CLI install <name> 命令执行流程：

1. 解析参数
   ├── name: 能力包名称
   ├── --version: 指定版本（默认 latest published）
   └── --client: 目标客户端（默认自动检测）

2. 请求 Hub API
   └── GET /packages/{name}/install-manifest?version={v}&client={c}
       → 返回 Install Manifest JSON

3. 安全确认（按信任评分分级）
   ├── score >= 80 且无高危权限 → 展示信息，确认安装
   ├── score 50-79 或存在中风险 → 展示详情，要求输入 y
   └── score < 50 或存在高危 → 展示风险清单，要求输入完整确认语句

4. 执行安装步骤
   ├── download → 下载包到临时目录
   ├── verify  → sha256 校验
   ├── extract → 解压（如需要）
   ├── copy / install → 安装到目标位置
   └── write_config → 写入客户端配置（如 MCP 配置）

5. 写入本地记录
   └── ~/.trusted-agent-hub/installed.json
       ├── name, version, installed_at
       ├── install_path
       ├── manifest_hash
       └── client
```

## 5. 本地安装记录格式

CLI 安装后写入 `~/.trusted-agent-hub/installed.json`：

```json
{
  "installed": [
    {
      "name": "code-review-skill",
      "version": "1.0.0",
      "type": "skill",
      "installed_at": "2026-07-04T10:30:00Z",
      "install_path": "/home/user/.claude/skills/code-review-skill/",
      "client": "claude-code",
      "manifest_hash": "sha256:abc123...",
      "source": {
        "type": "github",
        "repository_url": "https://github.com/alice-dev/code-review-skill",
        "commit_hash": "a1b2c3d4..."
      }
    }
  ],
  "last_updated": "2026-07-04T10:30:00Z"
}
```

## 6. CLI 命令输出格式建议

### search 命令输出

```
$ npx trusted-agent-hub search "code review"

找到 3 个结果：

  名称                    类型      版本     信任评分   安装量
  ─────────────────────────────────────────────────────────
  code-review-skill       skill     1.0.0    92 ✅      1.2k
  dev-toolkit-plugin      plugin    1.3.0    78 ⚠️      892
  git-helper-skill        skill     1.0.0    90 ✅      2.1k

使用 `install <name>` 安装，`info <name>` 查看详情。
```

### info 命令输出

```
$ npx trusted-agent-hub info code-review-skill

━━━ code-review-skill ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  类型:     Skill
  版本:     1.0.0
  作者:     Alice CodeReview Team
  许可证:   MIT
  信任评分: 92/100 (✅ 可信)

━━━ 权限声明 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  文件系统:  读 [./], 写 [./review-output/]
  Shell:     git, diff, grep
  网络:      无

━━━ 风险提示 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  风险等级: 可信
  安装建议: 安全安装

  使用 `install code-review-skill` 安装。
```

### install 命令输出

```
$ npx trusted-agent-hub install code-review-skill

即将安装 code-review-skill v1.0.0 (Skill)

  信任评分: 92/100 (✅ 可信)
  适配客户端: Claude Code

  权限:
    - 读取当前项目文件
    - 写入 ./review-output/ 目录
    - 执行 git, diff, grep 命令
    - 无网络访问

确认安装? [Y/n] y

  [1/4] 下载中... ✓ (24 KB)
  [2/4] 校验 SHA256... ✓
  [3/4] 解压到临时目录... ✓
  [4/4] 复制到 ~/.claude/skills/code-review-skill/... ✓

安装完成！使用 /review-pr 开始代码审查。
```
