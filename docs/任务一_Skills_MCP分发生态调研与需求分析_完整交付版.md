# 任务一：Skills / MCP 分发生态调研与需求分析完整交付版

> 撰写时间：2026-06-15  
> 课题名称：可信 Agent Skills 与 MCP Hub 平台设计与实现  
> 调研人员：B、A  
> AI 辅助撰写：Codex（GPT-5）  
> 文档定位：任务一最终调研文档，合并B已有调研内容，并补充A负责的社区市场、分发机制、核心对象细化、业务流程与需求设计。

## 1. 调研目标与分工

### 1.1 任务一目标

根据任务书，任务一需要完成“Skills / MCP 分发生态调研并完成需求设计”，具体包括：

- 调研 Claude Code 插件市场、Agent Skills、MCP Registry、社区 Skill Hub、GitHub 分发、`npx` 安装工具等现有方案。
- 梳理可信 Skills / MCP Hub 需要支持的核心对象，包括 Skill、MCP Server、Plugin、Subagent、Command、Prompt 等。
- 明确平台角色与业务流程，至少包括普通用户、提交者、审核员、管理员。
- 输出需求分析文档，覆盖浏览搜索、详情展示、提交审核、自动扫描、人工 Review、信任评分、CLI 安装、版本更新、下架与审计等流程。

### 1.2 调研分工

| 调研人 | 负责方向 | 本文档中的内容 |
|---|---|---|
| B | 供给侧、规范侧、安全侧 | Agent Skills、Claude Code 插件市场、MCP Registry、Skills 风险、审核启示、基础核心对象 |
| A | 消费侧、分发侧、需求设计侧 | 社区 Skill Hub、GitHub 分发、`npx` / npm 分发、Subagent / Command / Prompt 细化、角色流程、信任评分、需求分析 |

## 2. 现有生态调研

### 2.1 Agent Skills 体系

调研人：B

Agent Skills 是一种轻量级能力扩展机制。一个 Skill 通常是一个目录，核心文件是 `SKILL.md`，用于向智能体描述某类任务的工作流、约束、工具使用方式和参考资料。Skill 可以只有自然语言指令，也可以包含脚本、模板、参考文档和资源文件。

典型目录结构：

```txt
my-skill/
  SKILL.md
  scripts/
    helper.py
  resources/
    template.json
  references/
    api-docs.md
```

`SKILL.md` 通常使用 YAML frontmatter 声明元数据，正文提供指令内容：

```yaml
---
name: my-skill
description: A skill for doing X
version: 1.0.0
author: author-name
license: MIT
tools:
  - Read
  - Bash
model: claude-sonnet-4
---
```

主要结论：

- Skill 的本质不是普通代码包，而是“给智能体的可复用上下文与工作流”。
- Skill 风险不仅来自脚本，也来自自然语言指令本身。
- 可信 Hub 必须同时解析元数据、正文指令、附带脚本、依赖与资源文件。

对可信 Hub 的启示：

- 需要解析 `SKILL.md` frontmatter，并转化为统一能力包元数据。
- 需要扫描 Skill 正文中的提示注入、越权指令、凭据读取、外连要求等。
- 需要把工具权限、脚本文件、外部资源和依赖作为审核输入。

### 2.2 Claude Code 插件市场与插件规范

调研人：B

Claude Code 插件系统提供了较完整的能力包组织方式。一个 Plugin 可以聚合 Skills、Agents、Commands、Hooks、MCP Servers 等组件。插件市场通过 marketplace 索引文件进行发现，插件本体通过 `plugin.json` 或相关 manifest 描述能力内容。

插件生态可抽象为四层：

```txt
Marketplace 发现层
→ marketplace.json 索引层
→ plugin.json 元数据层
→ Skills / Agents / Commands / Hooks / MCP 能力层
```

`plugin.json` 对可信 Hub 的元数据设计有重要参考价值：

```json
{
  "name": "my-plugin",
  "description": "Plugin description",
  "version": "1.0.0",
  "author": "author-name",
  "license": "MIT",
  "homepage": "https://github.com/user/repo",
  "repository": "https://github.com/user/repo",
  "keywords": ["skill", "mcp"],
  "skills": ["./skills/my-skill"],
  "agents": ["./agents/my-agent"],
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["./mcp/server.py"]
    }
  },
  "settings": {
    "permissions": {}
  }
}
```

主要结论：

- Plugin 是复合能力包，比单个 Skill 或 MCP Server 更接近本课题的“能力包”概念。
- Marketplace 机制说明可信 Hub 可以优先做元数据索引，而不是一开始托管所有代码。
- 插件元数据中的版本、仓库、许可证、路径引用、权限声明、组件列表都应进入统一 Schema。

对可信 Hub 的启示：

- 统一元数据规范可以以插件 manifest 为骨架。
- Hub 需要支持单能力包和复合能力包两类形态。
- 版本更新既要支持 SemVer，也要支持 commit hash / release tag 等来源追踪。

### 2.3 MCP Registry 架构

调研人：B

MCP Registry 的核心理念是“元注册表”：Registry 记录 MCP Server 的元数据和来源指针，而实际代码可以托管在 npm、PyPI、Docker、GitHub 或远程服务中。

抽象结构：

```txt
MCP Registry
  记录元数据、包来源、版本、运行方式
    ↓
npm / PyPI / Docker / GitHub / Remote Server
  托管实际代码或服务
    ↓
MCP Client
  根据 manifest 安装或连接
```

MCP Registry 的关键机制：

| 机制 | 内容 | 对可信 Hub 的启示 |
|---|---|---|
| 元注册表 | 只记录来源、版本、运行方式和元数据 | Hub 可降低存储负担，重点管理可信证据 |
| 命名空间 | 通过 GitHub、域名或组织身份验证所有权 | 防止能力包抢名和冒名发布 |
| 多部署方式 | package、remote、hybrid | Hub 需要区分本地运行和远程服务风险 |
| API 查询 | 列表、详情、发布 API | 可借鉴 RESTful API 设计 |

主要结论：

- MCP Server 风险比普通 Skill 更偏“工具调用”和“外部数据访问”。
- MCP Server 需要声明运行命令、传输协议、工具列表、资源范围、认证方式和远程端点。
- 对远程 MCP Server，还要关注网络服务可信度、认证安全和数据出境风险。

### 2.4 社区 Skill Hub 与传统插件市场

调研人：A

社区中已经出现多种能力发现方式，但多数方案更关注“能找到、能安装”，尚未形成统一的可信审核标准。

| 平台 / 生态 | 主要能力 | 分发方式 | 可借鉴点 | 不足 |
|---|---|---|---|---|
| Claude Code Plugin Marketplace | 插件发现、安装、更新 | marketplace 索引 + 插件 manifest | 适合复合能力包；manifest 结构清晰 | 可信审核机制不适合直接照搬到内部治理 |
| MCP Registry | MCP Server 发现 | 元注册表 + 多包源 | 多来源接入、命名空间、API | 主要覆盖 MCP，不覆盖 Skill / Prompt / Command |
| GitHub 仓库集合 | 社区共享 Skills / MCP | README、目录、Release | 开源协作、版本历史透明 | 缺少统一元数据、评分、审核和安装前风险提示 |
| VS Code Marketplace / Open VSX | IDE 插件市场 | package.json + 市场审核 | 发布者、版本、评分、安装量、下架机制成熟 | 面向传统插件，不能直接识别提示注入风险 |
| npm Registry | CLI 与包分发 | npm 包 + `npx` / `npm exec` | 适合 CLI 工具分发；版本和完整性机制成熟 | 包生态存在依赖混淆、恶意包和供应链风险 |

主要结论：

- 现有市场机制可以解决发现、分类、版本、安装量、评分等问题。
- Agent 能力包的特殊性在于：自然语言指令也可能是攻击载体。
- 可信 Hub 的差异化能力应是：统一元数据、自动扫描、人工审核、信任评分、权限声明、证据链和审计日志。

### 2.5 GitHub 分发机制

调研人：A

GitHub 是 Skills / MCP / Plugin 最常见的来源之一。它既可以作为源码仓库，也可以通过 Releases 提供稳定版本包。

GitHub 分发方式：

| 模式 | 说明 | 优点 | 风险 |
|---|---|---|---|
| 仓库直接引用 | 保存 `owner/repo`、branch、tag、commit、子目录 | 简单、透明、便于审计 | branch 会漂移，仓库可能被转让或篡改 |
| Release Asset | 通过 GitHub Release 发布压缩包 | 适合稳定版本；可附带 changelog | 需要校验 asset hash 与 tag |
| Git Tag | 用 tag 标记版本 | 便于 SemVer 管理 | 轻量 tag 可能被移动，需要记录 commit |
| Commit Hash | 固定到具体提交 | 可追溯性最好 | 用户理解成本高 |
| GitHub Actions 构建 | 自动打包和发布 | 可形成 CI/CD 流程 | 构建环境和 workflow 本身也要审查 |

Hub 应记录的 GitHub 来源字段：

```txt
repository_url
owner
repo
source_type: branch | tag | commit | release
ref
commit_hash
release_asset_url
sha256
license
stars
last_commit_at
verified_owner
attestation_url
sbom_url
```

安全建议：

- 不允许只记录 `main` 分支作为可信版本，必须在发布版本中固化 commit hash。
- 对 Release Asset 需要保存 SHA256。
- 对 GitHub 来源，应区分未验证作者、已验证个人作者、已验证组织作者。
- GitHub Actions OIDC、artifact attestation、SBOM、Dependabot 结果可以作为信任评分的输入，但不能替代内容扫描。

### 2.6 `npx` / npm 分发机制

调研人：A

`npx` / `npm exec` 适合本课题 CLI 工具的分发。用户无需全局安装，即可运行：

```bash
npx trusted-agent-hub search <keyword>
npx trusted-agent-hub info <name>
npx trusted-agent-hub install <name>
npx trusted-agent-hub update <name>
```

需要区分两个层次：

```txt
npx 负责运行 trusted-agent-hub CLI
Hub API 负责提供可信能力包元数据、扫描报告和安装来源
CLI 负责下载、校验、写入本地智能体客户端配置
```

CLI 命令体系建议：

| 命令 | 功能 |
|---|---|
| `search <keyword>` | 搜索能力包 |
| `info <name>` | 查看详情、评分、权限、来源 |
| `install <name>` | 安装能力包 |
| `update <name>` | 更新已安装能力包 |
| `uninstall <name>` | 卸载能力包 |
| `verify <name>` | 校验本地安装文件完整性 |
| `list` | 查看已安装能力包 |
| `login` | 登录 Hub，用于提交、私有包安装或反馈 |

安装前置检查：

```txt
1. CLI 请求 Hub API 获取能力包元数据
2. 展示名称、版本、作者、来源、审核状态
3. 展示信任评分和主要扣分原因
4. 展示权限声明和风险标签
5. 下载包并校验 sha256 / signature
6. 写入目标客户端目录或配置文件
7. 生成本地安装记录，供 update / uninstall / verify 使用
```

安全确认策略：

| 条件 | 处理 |
|---|---|
| 信任分数 >= 80 且无高危权限 | 展示信息后确认安装 |
| 信任分数 50-79 或存在中风险项 | 要求用户输入 `y` 明确确认 |
| 信任分数 < 50 或存在高危权限 | 默认阻止，除非用户输入完整风险确认语句 |
| 未审核包 | 默认不允许普通用户安装，可给管理员或审核环境使用 |

主要结论：

- `npx` 解决的是 CLI 触达问题，不解决能力包可信问题。
- CLI 必须依赖 Hub 提供的审核状态、扫描结果和可信来源。
- CLI 自身也应使用 npm provenance、依赖锁定和版本发布规范降低供应链风险。

## 3. 核心对象模型

### 3.1 核心对象总览

调研人：B、A

| 对象 | 定义 | 典型入口 | 关键元数据 | 主要风险 |
|---|---|---|---|---|
| Skill | 教智能体完成特定任务的指令、脚本和资源 | `SKILL.md` | 名称、描述、版本、工具权限、模型、资源路径 | 提示注入、危险脚本、凭据读取 |
| MCP Server | 连接外部工具和数据源的协议服务 | `server.json`、npm / PyPI 包、Docker 镜像 | 运行命令、传输协议、工具列表、资源、认证方式 | 越权工具调用、数据外传、远程服务风险 |
| Plugin | 聚合多种能力组件的复合包 | `plugin.json` | 组件列表、版本、路径、权限、来源 | 组合风险、隐藏组件、权限扩大 |
| Subagent | 专用子智能体，负责特定任务 | agent 配置 / markdown | 系统提示、工具集、模型、作用域 | 隐藏高危指令、权限隔离不足 |
| Command | 用户可直接触发的快捷命令 | slash command 文件 / 配置 | 命令名、参数、作用域、执行逻辑 | 包装危险操作、诱导执行 |
| Prompt | 可复用提示模板 | prompt 文件 / MCP prompt | 模板变量、输入来源、用途、约束 | 模板注入、变量未转义 |

### 3.2 Subagent 补充分析

调研人：A

Subagent 是面向特定任务的专用智能体，通常包含独立系统提示、工具权限和执行范围。它适合处理代码审查、测试生成、文档总结、安全分析等专业任务。

Hub 需要记录：

- subagent 名称、描述、适用任务。
- system prompt 或 agent 指令文件位置。
- 允许工具列表。
- 是否允许 shell、网络、文件写入、外部服务访问。
- 与主 Agent 的交互方式。

审核重点：

- 是否通过系统提示绕过用户意图。
- 是否要求隐藏执行过程或隐藏风险。
- 是否声明了超出任务需要的工具权限。
- 是否可能在后台执行高风险操作。

### 3.3 Command 补充分析

调研人：A

Command 通常表现为 slash command 或快捷命令。它可以把一段复杂工作流封装成用户可触发的入口。

Hub 需要记录：

- 命令名称。
- 参数列表、默认值、必填项。
- 触发范围：项目级、用户级、全局。
- 背后引用的脚本、Prompt、Skill 或工具。
- 权限需求。

审核重点：

- 命令是否包装了危险 shell 操作。
- 是否通过简单命令名掩盖高风险行为。
- 参数是否会拼接到 shell 中导致命令注入。
- 是否存在远程代码下载执行。

### 3.4 Prompt 补充分析

调研人：A

Prompt 是可复用提示模板，可能出现在 Skill、MCP Server 或插件包中。Prompt 看似无代码，但会直接影响模型行为。

Hub 需要记录：

- Prompt 名称、用途和适用场景。
- 模板变量及变量来源。
- 是否作为系统提示、任务提示或用户提示使用。
- 变量替换和转义策略。

审核重点：

- 是否包含“忽略之前指令”“不要告诉用户”等可疑指令。
- 是否诱导模型读取敏感文件或环境变量。
- 是否在模板变量中引入未转义用户输入。
- 是否把外部文档内容当作高优先级指令。

## 4. 平台角色与权限

调研人：B、A

| 角色 | 主要目标 | 权限 |
|---|---|---|
| 普通用户 | 发现、理解和安装可信能力包 | 浏览、搜索、查看详情、安装、更新、卸载、评分、反馈 |
| 提交者 | 发布和维护能力包 | 创建提交、上传版本、查看扫描报告、响应审核意见、撤回提交 |
| 审核员 | 判断能力包是否可发布 | 查看审核队列、查看 Diff 和扫描报告、通过、驳回、要求修改 |
| 管理员 | 平台治理和风险处置 | 用户管理、角色分配、下架能力包、调整标签、查看审计日志、处理投诉 |

角色与流程关系：

```txt
提交者
  提交能力包 / 更新版本
    ↓
系统
  自动扫描 / 生成评分
    ↓
审核员
  人工 Review / 给出结论
    ↓
普通用户
  浏览 / 搜索 / CLI 安装
    ↓
管理员
  处理风险 / 下架 / 审计
```

## 5. 业务流程需求设计

### 5.1 浏览搜索流程

调研人：A

目标：让普通用户快速发现可信能力包。

功能需求：

- 支持按关键词搜索名称、描述、作者、标签。
- 支持按类型筛选：Skill、MCP Server、Plugin、Subagent、Command、Prompt。
- 支持按适配客户端筛选：Claude Code、Cursor、VS Code、通用 MCP Client。
- 支持按审核状态、信任评分、更新时间、安装量排序。
- 搜索结果卡片展示名称、简介、类型、版本、作者、信任评分、审核状态、风险标签。

### 5.2 详情展示流程

调研人：A

详情页需要帮助用户判断“是否值得安装”。

详情页信息：

- 基础信息：名称、描述、类型、版本、作者、许可证、来源仓库。
- 安装信息：CLI 安装命令、目标客户端配置、依赖要求。
- 安全信息：审核状态、信任评分、评分解释、权限声明、扫描报告摘要。
- 版本信息：版本历史、changelog、发布时间、hash。
- 社区信息：安装量、评分、评论、问题反馈。

权限展示建议：

| 权限类型 | 展示方式 |
|---|---|
| 文件读取 | 展示允许路径和敏感路径警告 |
| 文件写入 | 展示写入范围和覆盖风险 |
| Shell 执行 | 标红展示命令类型 |
| 网络访问 | 展示外连域名和协议 |
| 环境变量读取 | 展示变量类别，敏感值脱敏 |
| 外部服务认证 | 展示 token / OAuth / API Key 要求 |

### 5.3 提交审核流程

调研人：A

提交入口支持多来源：

- GitHub 仓库。
- GitHub Release Asset。
- npm 包。
- PyPI 包。
- Docker 镜像。
- 本地压缩包。
- 人工上传。

提交流程：

```txt
1. 提交者填写基础信息
2. 选择能力包类型和来源
3. 上传或填写 manifest / SKILL.md / MCP 配置
4. 声明权限、依赖、入口文件和适配客户端
5. 系统解析元数据
6. 进入自动扫描
7. 扫描完成后进入人工审核队列
```

提交状态：

```txt
draft
submitted
scanning
scan_failed
pending_review
changes_requested
approved
rejected
published
yanked
```

### 5.4 自动扫描流程

调研人：B、A

自动扫描需要覆盖任务书要求的风险类型。

| 扫描项 | 检测内容 | 输出 |
|---|---|---|
| 结构校验 | 是否存在必要文件，如 `SKILL.md`、`plugin.json`、MCP manifest | pass / fail |
| 元数据校验 | 名称、版本、作者、许可证、来源、入口、权限是否完整 | 缺失字段 |
| 提示注入 | 忽略指令、隐藏行为、绕过审核、欺骗用户 | 可疑片段和行号 |
| 危险命令 | `rm -rf`、`curl | bash`、`eval`、`chmod 777` 等 | 命令和严重等级 |
| 敏感信息 | token、secret、private key、password | 脱敏位置 |
| 环境变量读取 | `$AWS_*`、`GITHUB_TOKEN`、`NPM_TOKEN` 等 | 变量类别 |
| 网络外连 | curl、wget、fetch、requests、未知域名 | 域名和用途 |
| 远程代码执行 | 下载脚本后执行、动态 eval | 阻断项 |
| 文件系统越权 | 访问 `~/.ssh`、`/etc/passwd`、项目外路径 | 路径和风险 |
| 依赖风险 | npm / pip 漏洞、未锁定版本、可疑包名 | 依赖报告 |

扫描报告结构建议：

```json
{
  "scan_id": "uuid",
  "package_id": "uuid",
  "version": "1.0.0",
  "overall_result": "pass|warning|block",
  "started_at": "2026-06-15T10:00:00Z",
  "finished_at": "2026-06-15T10:00:30Z",
  "findings": [
    {
      "rule_id": "PI-001",
      "severity": "high",
      "file": "SKILL.md",
      "line": 42,
      "title": "可疑提示注入指令",
      "description": "检测到要求模型隐藏行为的语句",
      "recommendation": "删除该指令或改为透明提示"
    }
  ]
}
```

### 5.5 人工 Review 流程

调研人：A

审核员工作台应提供：

- 待审核队列。
- 提交详情。
- 当前版本与上一版本 Diff。
- 自动扫描报告。
- 权限声明与实际代码匹配结果。
- 许可证与来源信息。
- 审核结论输入框。

审核结论：

| 结论 | 含义 |
|---|---|
| 通过 | 可发布，生成发布记录 |
| 驳回 | 不允许发布，需要记录原因 |
| 要求修改 | 返回提交者，提交者可重新提交 |

人工审核清单：

- 功能描述是否真实。
- 权限是否最小化。
- 扫描警告是否可接受。
- 是否存在隐藏指令或欺骗性说明。
- 依赖是否可信。
- 来源和许可证是否清晰。
- 安装命令是否安全。

### 5.6 信任评分流程

调研人：A

信任评分采用 0-100 分，并必须可解释。

| 维度 | 分值 | 说明 |
|---|---:|---|
| 来源可信度 | 20 | 来源是否可验证，是否固定 commit / tag，是否有组织认证 |
| 作者信誉 | 10 | 作者历史提交、审核通过率、违规记录 |
| 元数据完整性 | 10 | manifest、许可证、入口、权限、依赖是否完整 |
| 权限最小化 | 15 | 工具、文件、网络、环境变量权限是否合理 |
| 自动扫描结果 | 20 | 高危 / 中危 / 低危发现数量 |
| 人工审核结论 | 10 | 是否通过人工 Review |
| 版本稳定性 | 5 | SemVer、changelog、更新频率、回滚记录 |
| 用户反馈 | 5 | 安装量、评分、问题报告 |
| 签名与可追溯性 | 5 | hash、签名、attestation、SBOM |

评分解释示例：

```txt
信任评分：72 / 100
风险等级：中等

扣分原因：
- 来源仓库未通过组织认证：-5
- 需要 Bash 执行权限和项目目录写权限：-8
- 扫描发现 1 处读取 GITHUB_TOKEN 的代码路径：-7
- 当前版本没有签名或构建证明：-4

建议：
安装前确认该 Skill 是否确实需要读取 GitHub token；建议在隔离项目中试用。
```

### 5.7 CLI 安装流程

调研人：A

CLI 安装主流程：

```txt
npx trusted-agent-hub install <name>
  ↓
查询 Hub API
  ↓
展示元数据、评分、权限、风险
  ↓
用户确认
  ↓
下载能力包
  ↓
校验 hash / signature
  ↓
写入目标客户端目录或配置文件
  ↓
记录本地安装 manifest
```

CLI 目标客户端适配：

| 客户端 | 安装目标 |
|---|---|
| Claude Code Skill | 用户级或项目级 skills 目录 |
| Claude Code Plugin | 插件目录或 marketplace 安装记录 |
| MCP Client | MCP 配置文件 |
| Cursor / VS Code | 对应扩展或 agent 配置目录 |
| 通用 | 用户指定目录 |

### 5.8 版本更新流程

调研人：A

版本更新流程：

```txt
1. CLI 检查本地安装版本
2. 请求 Hub 获取最新已发布版本
3. 展示 changelog、Diff 摘要、评分变化、权限变化
4. 用户确认更新
5. 下载新版本并校验
6. 替换旧版本
7. 保存旧版本备份和本地安装记录
```

更新风险提示：

- 新版本新增 Bash、网络、环境变量权限时必须提示。
- 新版本信任评分下降超过阈值时必须提示。
- 新版本扫描结果从 pass 变为 warning / block 时禁止自动更新。

### 5.9 下架与审计流程

调研人：A

下架触发条件：

- 发现安全漏洞或恶意行为。
- 审核结论被撤回。
- 作者主动申请。
- 许可证或合规问题。
- 用户投诉成立。
- 管理员风险处置。

下架流程：

```txt
管理员发起下架
  ↓
填写下架原因和影响范围
  ↓
能力包状态变为 yanked
  ↓
Web 端停止推荐和安装
  ↓
CLI 查询 / 更新时提示风险
  ↓
审计日志记录操作
```

审计日志字段：

```txt
actor_id
actor_role
action
target_type
target_id
before_state
after_state
reason
created_at
request_ip
```

## 6. 需求分析汇总

### 6.1 功能性需求

调研人：A

| 编号 | 模块 | 需求 |
|---|---|---|
| FR-01 | 浏览搜索 | 用户可以搜索、筛选、排序能力包 |
| FR-02 | 详情展示 | 用户可以查看能力包详情、权限、评分、扫描结果 |
| FR-03 | 提交 | 提交者可以通过多来源提交能力包 |
| FR-04 | 自动扫描 | 系统自动执行结构、元数据、安全和依赖扫描 |
| FR-05 | 人工审核 | 审核员可以查看报告并做出审核结论 |
| FR-06 | 信任评分 | 系统生成 0-100 分评分和扣分解释 |
| FR-07 | CLI 安装 | 用户可以通过 `npx` 搜索、查看、安装、更新、卸载、校验 |
| FR-08 | 版本管理 | 平台支持版本发布、更新检测、changelog 和回滚信息 |
| FR-09 | 下架审计 | 管理员可以下架能力包并查看审计日志 |
| FR-10 | 用户反馈 | 用户可以评分、评论、举报问题 |

### 6.2 非功能性需求

调研人：A

| 类型 | 需求 |
|---|---|
| 安全性 | 未经审核的包默认不可发布；高危扫描结果默认阻断 |
| 可追溯性 | 每个版本必须保存来源、hash、manifest、扫描报告、审核记录和评分解释 |
| 可扩展性 | 支持新增能力类型、扫描规则、来源类型和客户端适配 |
| 可用性 | 普通用户能在安装前理解风险，不需要阅读完整源码才能决策 |
| 可维护性 | 元数据 Schema、扫描报告格式、API 契约和状态机应稳定 |
| 性能 | 搜索、详情、安装元数据查询应满足交互式响应需求 |

## 7. 对后续任务的输入

调研人：B、A

| 后续任务 | 本调研提供的输入 |
|---|---|
| 任务二：元数据规范 | 核心对象模型、多来源字段、权限声明、风险标签、安装方式 |
| 任务三：后端与数据模型 | 用户、能力包、版本、扫描报告、审核记录、信任评分、安装记录、审计日志 |
| 任务四：Web Hub | 浏览搜索、详情页、提交页、审核页、管理员页的信息架构 |
| 任务五：CLI / NPX | CLI 命令体系、安装前确认、校验、更新、卸载、本地记录 |
| 任务六：扫描与评分 | 扫描规则清单、评分权重、评分解释格式 |
| 任务七：测试与示范数据 | 高可信样例、待确认样例、风险样例的分类依据 |

## 8. 参考资料

| 序号 | 资料 | URL | 调研人 |
|---|---|---|---|
| 1 | Claude Code Skills 文档 | https://code.claude.com/docs/en/skills | B |
| 2 | Claude Code 插件发现与安装 | https://code.claude.com/docs/en/discover-plugins | B |
| 3 | Claude Code 插件创建与审核机制 | https://code.claude.com/docs/en/plugins | B |
| 4 | Claude Code 插件参考 | https://code.claude.com/docs/en/plugins-reference | B |
| 5 | Claude Code 插件市场创建 | https://code.claude.com/docs/en/plugin-marketplaces | A |
| 6 | MCP Registry | https://modelcontextprotocol.info/tools/registry/ | B |
| 7 | MCP 官方文档 | https://modelcontextprotocol.io/docs/getting-started/intro | A |
| 8 | Anthropic Agent Skills 设计文章 | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | B |
| 9 | Agent Skills Open Standard | https://agentskills.io/specification | A |
| 10 | Claude Code Subagents | https://code.claude.com/docs/en/sub-agents | A |
| 11 | Claude Code Commands | https://code.claude.com/docs/en/commands | A |
| 12 | MCP Prompts 规范 | https://modelcontextprotocol.io/specification/2025-06-18/server/prompts | A |
| 13 | npm npx 文档 | https://docs.npmjs.com/cli/v8/commands/npx/ | A |
| 14 | npm exec 文档 | https://docs.npmjs.com/cli/v8/commands/npm-exec | A |
| 15 | npm provenance | https://docs.npmjs.com/generating-provenance-statements/ | A |
| 16 | GitHub Artifact Attestations | https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds | A |
| 17 | VS Code Extension Marketplace | https://code.visualstudio.com/docs/configure/extensions/extension-marketplace | A |
| 18 | VS Code Publishing Extensions | https://code.visualstudio.com/api/working-with-extensions/publishing-extension | A |
| 19 | OWASP Agentic Skills Top 10 | https://owasp.org/www-project-agentic-skills-top-10/ | B |
| 20 | OWASP Top 10 for LLM Applications | https://owasp.org/www-project-top-10-for-large-language-model-applications/ | B |

## 9. 最终结论

调研人：B、A

现有 Skills / MCP 生态已经具备基础的发现、安装和分发能力，但整体仍处于早期阶段。Claude Code 插件市场、MCP Registry、GitHub、npm / npx、传统 IDE 插件市场分别提供了 manifest、元注册表、多来源托管、CLI 分发、评分与下架等可借鉴机制。

可信 Agent Skills 与 MCP Hub 的核心价值不应只是“再做一个市场”，而应是建立可信治理层：

- 用统一元数据描述 Skill、MCP Server、Plugin、Subagent、Command、Prompt。
- 用自动扫描识别提示注入、危险命令、凭据读取、网络外连、依赖风险等问题。
- 用人工 Review 弥补自动化扫描对自然语言语义和业务合理性的不足。
- 用 0-100 分信任评分和扣分解释帮助用户理解风险。
- 用 `npx` CLI 把可信元数据、权限声明和安装动作连接起来。
- 用版本、hash、来源、扫描报告、审核记录和审计日志形成可追溯证据链。

因此，任务一完成后，后续平台实现应围绕一条主线展开：

```txt
提交能力包
→ 解析统一元数据
→ 自动扫描
→ 生成扫描报告和信任评分
→ 人工审核
→ 发布到 Web Hub
→ 用户查看详情
→ CLI 安装并校验
→ 版本更新、反馈、下架与审计
```

这条主线能够直接支撑任务书中对 Web Hub、后端 API、CLI 工具、审核机制、信任评分和验收演示的要求。
