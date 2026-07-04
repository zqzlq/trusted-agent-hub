# 可信能力包元数据规范

> 版本：v0.1  
> 冻结时间：第 2 周中  
> 关联文档：`packages/schema/agent-package.schema.json`

## 1. 设计目标

本规范定义面向 Agent Skills、MCP Server、Plugin、Subagent、Command、Prompt 等能力单元的统一元数据格式。目标如下：

- **类型统一**：六种能力包类型映射到同一 Schema，避免每个类型单独定义格式。
- **来源可追溯**：每个版本必须记录来源仓库、ref、commit hash 和内容校验值。
- **权限可审查**：所有能力包必须声明权限范围，供扫描器、审核员和用户评估风险。
- **安装可执行**：元数据中包含足够信息，使 CLI 和 Web 能生成正确的安装命令。
- **风险可计算**：元数据作为扫描器和评分模型的输入，支持自动化风险判定。

## 2. 能力包类型

| 类型 | type 值 | 定义 | 核心入口文件 |
|------|---------|------|-------------|
| Skill | `skill` | 面向特定任务的指令、脚本和资源集合 | `SKILL.md` |
| MCP Server | `mcp_server` | 通过 MCP 协议提供工具/资源/服务的服务端 | `server.json` / `package.json` / `pyproject.toml` |
| Plugin | `plugin` | 聚合多种能力组件的复合包 | `plugin.json` / `.claude-plugin/plugin.json` |
| Subagent | `subagent` | 面向特定任务的专用子智能体 | agent 配置 / markdown |
| Command | `command` | 用户可直接触发的快捷命令 | slash command 文件 |
| Prompt | `prompt` | 可复用的提示模板 | prompt 模板文件 |

## 3. 统一元数据字段

### 3.1 顶层结构

```jsonc
{
  // ===== 必填：基础标识 =====
  "name": "string",              // 能力包唯一名称，kebab-case，如 "code-review-skill"
  "version": "string",           // SemVer 版本号，如 "1.0.0"
  "type": "string",              // skill | mcp_server | plugin | subagent | command | prompt
  "description": "string",       // 一句话描述
  "author": {                    // 作者信息
    "name": "string",
    "email": "string",
    "url": "string"              // 可选，GitHub 主页等
  },
  "license": "string",           // SPDX 标识符，如 "MIT", "Apache-2.0"

  // ===== 必填：来源信息 =====
  "source": {
    "type": "string",            // github | npm | pypi | docker | local_upload
    "repository_url": "string",  // 仓库 HTTPS URL
    "owner": "string",           // 仓库所有者（GitHub org/user）
    "repo": "string",            // 仓库名称
    "ref_type": "string",        // branch | tag | commit | release
    "ref": "string",             // tag 名 / branch 名 / release 名
    "commit_hash": "string",     // 锁定 commit hash（40 字符 hex）
    "subdirectory": "string"     // 可选，monorepo 子目录路径
  },

  // ===== 必填：内容校验 =====
  "integrity": {
    "sha256": "string",          // 包内容 SHA256（压缩包或目录）
    "signature": "string"        // 可选，PGP / Sigstore 签名
  },

  // ===== 必填：适配客户端 =====
  "compatibility": ["string"],   // 枚举值，见第 4 节

  // ===== 可选：标签与分类 =====
  "keywords": ["string"],
  "category": "string",          // 如 "code-generation", "security", "data"
  "homepage": "string",          // 项目主页或文档 URL
  "icon": "string",              // 图标 URL 或 base64

  // ===== 可选：依赖声明 =====
  "dependencies": {
    "npm": [{"name": "string", "version": "string"}],
    "pip": [{"name": "string", "version": "string"}],
    "system": ["string"],        // 系统命令，如 "git", "docker"
    "docker": [{"image": "string", "tag": "string"}],
    "mcp_servers": [{"name": "string", "url": "string"}]
  },

  // ===== 必填：权限声明 =====
  "permissions": {},             // 见第 5 节

  // ===== 必填：安装方式 =====
  "installation": {},            // 见第 6 节

  // ===== 按类型条件必填 =====
  "skill_config": {},            // type=skill 时必填
  "mcp_server_config": {},       // type=mcp_server 时必填
  "plugin_config": {},           // type=plugin 时必填
  "subagent_config": {},         // type=subagent 时必填
  "command_config": {},          // type=command 时必填
  "prompt_config": {},           // type=prompt 时必填

  // ===== 可选：入口文件 =====
  "entry_points": {
    "main": "string",            // 主入口文件路径
    "config": "string",          // 配置文件路径
    "scripts": ["string"]        // 脚本文件列表
  }
}
```

### 3.2 字段约束速查

| 字段路径 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| `name` | string | ✅ | kebab-case，3-64 字符，`[a-z0-9-]+` |
| `version` | string | ✅ | SemVer 2.0，`major.minor.patch` |
| `type` | enum | ✅ | skill / mcp_server / plugin / subagent / command / prompt |
| `description` | string | ✅ | 10-200 字符 |
| `author.name` | string | ✅ | 1-100 字符 |
| `author.email` | string | ✅ | RFC 5322 邮箱格式 |
| `author.url` | string | ❌ | HTTPS URL |
| `license` | enum | ✅ | SPDX license identifier |
| `source.type` | enum | ✅ | github / npm / pypi / docker / local_upload |
| `source.repository_url` | string | ✅ | HTTPS URL |
| `source.ref` | string | ✅ | tag / branch / release 名 |
| `source.commit_hash` | string | ✅ | 40 字符 hex |
| `source.subdirectory` | string | ❌ | 相对路径 |
| `integrity.sha256` | string | ✅ | 64 字符 hex |
| `integrity.signature` | string | ❌ | PGP / Sigstore 签名 |
| `compatibility` | array | ✅ | 至少 1 个，见第 4 节 |
| `keywords` | array | ❌ | 每项 1-30 字符 |
| `category` | string | ❌ | 分类标识 |
| `homepage` | string | ❌ | HTTPS URL |
| `icon` | string | ❌ | URL 或 data URI |

## 4. 客户端兼容性

`compatibility` 数组至少包含一个：

| 枚举值 | 说明 |
|--------|------|
| `claude-code` | Claude Code CLI / 桌面版 |
| `claude-ai` | claude.ai web 界面 |
| `cursor` | Cursor IDE |
| `vscode` | VS Code |
| `mcp-client-generic` | 通用 MCP 客户端 |
| `openai-agents` | OpenAI Agents SDK |
| `github-copilot` | GitHub Copilot |
| `windsurf` | Windsurf IDE |
| `cline` | Cline (VS Code Extension) |

## 5. 权限声明规范

### 5.1 权限字段

```jsonc
"permissions": {
  "filesystem": {
    "read": ["string"],          // 可读路径，如 ["./"] 表示当前目录
    "write": ["string"],         // 可写路径
    "delete": false              // 是否允许删除
  },
  "shell": {
    "allowed": true,             // 是否允许执行 shell 命令
    "commands": ["string"],      // 白名单命令，空数组 = 任意命令
    "description": "string"      // 说明为什么需要 shell 权限
  },
  "network": {
    "allowed": true,
    "domains": ["string"],       // 允许访问的域名白名单，空 = 任意
    "description": "string"
  },
  "environment": {
    "read": ["string"],          // 可读取的环境变量名
    "write": ["string"]          // 可写入的环境变量名
  },
  "credentials": {
    "access": ["string"],        // 需要访问的凭据类型：api_key, ssh_key, token, password
    "description": "string"
  },
  "database": {
    "allowed": true,
    "drivers": ["string"],       // sqlite, postgresql, mysql 等
    "description": "string"
  },
  "browser": {
    "allowed": true,
    "description": "string"
  },
  "external_services": [{       // 调用的外部服务
    "name": "string",
    "url": "string",
    "description": "string"
  }]
}
```

### 5.2 权限风险等级

| 权限 | 低风险 | 中风险 | 高风险 |
|------|--------|--------|--------|
| filesystem.read | 特定文件/目录 | 整个项目目录 | `/`, `~`, 系统目录 |
| filesystem.write | `./output/` 等限定目录 | 整个项目目录 | `/`, `~`, 系统目录, `.git/` |
| filesystem.delete | false | 限定目录 | true（任意删除） |
| shell | false | 白名单命令 | true + 任意命令 |
| network | false | 白名单域名 | true + 任意域名 |
| environment.read | 特定变量 | 项目相关变量 | `*` 所有变量 |
| environment.write | false | 特定变量 | `PATH`, `PYTHONPATH` 等 |
| credentials | 无 | api_key, token（限定服务） | ssh_key, password |
| database | false | 只读 | 读写 |
| browser | false | 特定 URL | 任意 URL |

## 6. 安装方式规范

### 6.1 安装字段

```jsonc
"installation": {
  "method": "string",            // copy_directory | npm_install | pip_install | docker_run | manual_steps
  "targets": [{                  // 安装目标
    "client": "string",          // claude-code | cursor | vscode | mcp-client-generic …
    "destination": "string",     // 目标路径或配置说明
    "config_template": "string"  // 可选，配置模板（可包含 ${var} 占位符）
  }],
  "command": "string",           // method=manual_steps 时的安装说明
  "pre_install_message": "string",  // 可选，安装前提示
  "post_install_message": "string"  // 可选，安装后提示
}
```

### 6.2 安装方式说明

| method | 说明 | 示例 |
|--------|------|------|
| `copy_directory` | 解压或复制到目标目录 | Skill 解压到 `~/.claude/skills/` |
| `npm_install` | 通过 npm 安装 | `npm install -g my-skill` |
| `pip_install` | 通过 pip 安装 | `pip install my-mcp-server` |
| `docker_run` | 拉取并运行 Docker 镜像 | `docker run my-server` |
| `manual_steps` | 人工执行安装步骤 | 按 README 手动配置 |

## 7. 各类型专属配置

### 7.1 Skill 配置 (`type=skill`)

```jsonc
"skill_config": {
  "skill_md_path": "string",     // SKILL.md 文件路径，如 "./SKILL.md"
  "model": "string",             // 推荐模型，如 "claude-sonnet-4"
  "tools": ["string"],           // 声明使用的工具：Read, Write, Bash, Grep, Glob, WebFetch, WebSearch…
  "resources": ["string"],       // 资源文件或目录列表
  "references": ["string"]       // 参考文档列表
}
```

### 7.2 MCP Server 配置 (`type=mcp_server`)

```jsonc
"mcp_server_config": {
  "transport": "string",         // stdio | sse | streamable-http
  "command": "string",           // 启动命令，如 "python" / "node"
  "args": ["string"],            // 启动参数
  "env": {},                     // 需要的环境变量（仅声明名称，不包含值）
  "tools": [{"name": "string", "description": "string"}],
  "resources": [{"uri": "string", "description": "string"}],
  "prompts": [{"name": "string", "description": "string"}],
  "remote_endpoint": "string"    // 远程服务 URL（transport=sse 时）
}
```

### 7.3 Plugin 配置 (`type=plugin`)

```jsonc
"plugin_config": {
  "components": {
    "skills": ["string"],        // 引用的 Skill 路径
    "agents": ["string"],        // 引用的 Agent 路径
    "commands": ["string"],      // 引用的 Command 路径
    "mcp_servers": [{            // 内嵌 MCP Server
      "name": "string",
      "command": "string",
      "args": ["string"]
    }]
  },
  "hooks": ["string"],           // 生命周期 hooks
  "settings_schema": {}          // 用户可配置项 Schema
}
```

### 7.4 Subagent 配置 (`type=subagent`)

```jsonc
"subagent_config": {
  "system_prompt_path": "string",  // 系统提示文件路径
  "tools": ["string"],             // 允许使用的工具
  "model": "string",               // 推荐模型
  "scope": "string",               // project | user | global
  "max_iterations": 10,            // 最大迭代次数
  "interaction_mode": "string"     // autonomous | supervised
}
```

### 7.5 Command 配置 (`type=command`)

```jsonc
"command_config": {
  "command_name": "string",        // 命令名，如 "review-pr"
  "parameters": [{                 // 参数定义
    "name": "string",
    "type": "string",
    "required": false,
    "default": "string",
    "description": "string"
  }],
  "scope": "string",               // project | user | global
  "executor": "string",            // script | prompt | skill 引用
  "executor_path": "string"        // 执行入口路径
}
```

### 7.6 Prompt 配置 (`type=prompt`)

```jsonc
"prompt_config": {
  "prompt_path": "string",         // 模板文件路径
  "variables": [{                  // 模板变量
    "name": "string",
    "type": "string",
    "required": false,
    "default": "string",
    "description": "string"
  }],
  "role": "string",                // system | user | assistant | tool
  "escape_strategy": "string"      // none | html | markdown_code_fence
}
```

## 8. 风险标签

### 8.1 风险标签定义

风险标签由扫描器自动注入，也可由审核员手动添加：

| 标签 | 级别 | 说明 |
|------|------|------|
| `prompt-injection-suspect` | high | 发现疑似提示注入指令 |
| `dangerous-shell` | high | 包含危险 shell 命令（rm -rf, curl|bash 等） |
| `reads-credentials` | high | 读取凭据相关环境变量或文件 |
| `hardcoded-secret` | high | 包含硬编码密钥/令牌 |
| `remote-code-exec` | high | 从远程下载并执行代码 |
| `excessive-filesystem-read` | medium | 读取权限超出合理范围 |
| `excessive-filesystem-write` | medium | 写入权限超出合理范围 |
| `network-external` | medium | 访问外部网络 |
| `unlocked-dependency` | medium | 依赖版本未锁定 |
| `suspicious-dependency` | medium | 依赖来自可疑来源 |
| `unverified-source` | medium | 来源仓库未经验证 |
| `missing-integrity` | low | 缺少内容校验值 |
| `no-license` | low | 未声明许可证 |
| `incomplete-metadata` | low | 元数据不完整 |
| `undocumented-permission` | low | 有未声明的权限行为 |

### 8.2 风险等级与处置

| 级别 | 默认处置 |
|------|---------|
| `high` | 阻断发布，必须修复或提供充分人工审核理由 |
| `medium` | 允许发布但必须在详情页显著展示 |
| `low` | 记录但不阻断，降低信任评分 |

## 9. 审核状态机

### 9.1 状态枚举

```txt
draft → submitted → scanning → pending_review → approved → published
                       ↓            ↓               ↓
                      error      rejected        yanked
                                     ↓
                                resubmitted → scanning …
```

### 9.2 状态说明

| 状态 | 说明 | 触发者 |
|------|------|--------|
| `draft` | 提交者正在编辑，尚未正式提交 | 提交者 |
| `submitted` | 已正式提交，等待进入扫描队列 | 系统 |
| `scanning` | 自动扫描中 | 系统 |
| `error` | 扫描或处理失败 | 系统 |
| `pending_review` | 扫描完成，等待人工审核 | 系统 |
| `approved` | 审核通过，待发布 | 审核员 |
| `rejected` | 审核驳回 | 审核员 |
| `published` | 已发布到 Hub | 系统/审核员 |
| `yanked` | 已下架（从 Hub 撤下） | 管理员 |
| `resubmitted` | 驳回后重新提交 | 提交者 |

## 10. 完整示例

参见：

- `packages/schema/examples/skill-basic.json`
- `packages/schema/examples/mcp-server-basic.json`
- `packages/schema/examples/plugin-basic.json`
- `packages/schema/examples/risky-skill.json`

## 11. 版本管理规范

- **版本格式**：严格遵循 SemVer 2.0 (`MAJOR.MINOR.PATCH`)
- **来源锁定**：每个版本必须记录 `commit_hash` 和 `sha256`
- **不可变**：已发布的版本元数据不可修改，新版本必须创建新记录
- **更新提示**：CLI 安装前应提示当前安装版本与新版本差异

## 12. 扩展性约定

- 所有对象允许 `"$comment"` 和 `"x-*"` 前缀的自定义扩展字段
- 正式字段变更必须更新 Schema 版本号
- 字段废弃需要至少一个版本过渡期
