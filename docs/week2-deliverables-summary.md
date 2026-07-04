# 第二周交付物总览

> 状态：✅ 全部完成  
> 日期：2026-07-04  
> 下一阶段：第 3 周 — B 开始 Web + CLI 开发，A 开始 API 后端开发

## 交付清单

| # | 交付物 | 文件 | 状态 |
|---|--------|------|------|
| 1 | 元数据规范 | `docs/metadata-spec.md` | ✅ |
| 2 | 统一能力包 Schema | `packages/schema/agent-package.schema.json` | ✅ |
| 3 | 扫描报告 Schema | `packages/schema/scan-report.schema.json` | ✅ |
| 4 | 信任评分 Schema | `packages/schema/trust-score.schema.json` | ✅ |
| 5 | 数据库 ER 图与模型 | `docs/database-er-model.md` | ✅ |
| 6 | OpenAPI v0.1 契约 | `docs/openapi-v0.1.yaml` | ✅ |
| 7 | TS 共享常量 | `packages/schema/constants.ts` | ✅ |
| 8 | Python 共享常量 | `packages/schema/constants.py` | ✅ |
| 9 | 安装 Manifest 规范 | `docs/install-manifest-spec.md` | ✅ |
| 10 | Mock 数据 | `packages/schema/mock/` | ✅ |
| 11 | 示例元数据 | `packages/schema/examples/` | ✅ |
| 12 | 示例能力包 | `examples/` | ✅ |
| 13 | 项目目录结构 | `apps/`, `packages/`, `scanners/`, `deploy/` | ✅ |

## B (chengyuan B) 可以开始的工作

### Web 前端 (Next.js)

基于以下文件即可开始开发：

| 参考文件 | 用途 |
|---------|------|
| `docs/openapi-v0.1.yaml` | 所有 API 接口定义（响应格式、参数） |
| `packages/schema/mock/packages.json` | 首页列表 mock 数据 |
| `packages/schema/mock/versions/` | 详情页 mock 数据 |
| `packages/schema/constants.ts` | 所有枚举值和状态映射 |
| `docs/install-manifest-spec.md` | CLI 输出格式参考（Web 安装说明渲染） |

建议开发顺序：
1. 首页能力包列表（搜索、筛选、排序）
2. 能力包详情页（基础信息 + 权限 + 评分）
3. 审核状态和风险展示
4. 搜索和分页

### CLI (TypeScript + Commander)

| 参考文件 | 用途 |
|---------|------|
| `docs/install-manifest-spec.md` | 安装流程定义、命令输出格式 |
| `packages/schema/mock/packages.json` | search 命令 mock 数据 |
| `packages/schema/mock/versions/` | info 命令 mock 数据 |
| `packages/schema/constants.ts` | 所有常量和类型 |

建议开发顺序：
1. `search <keyword>` 命令
2. `info <name>` 命令
3. `install <name>` 命令（先 mock，等 API 就绪后切换）
4. `list` / `uninstall` / `verify`

## A 可以开始的工作

### 后端 API (FastAPI)

| 参考文件 | 用途 |
|---------|------|
| `docs/openapi-v0.1.yaml` | 接口契约 |
| `docs/database-er-model.md` | 数据库表结构 |
| `packages/schema/constants.py` | 所有枚举和状态机 |

建议开发顺序：
1. 数据库迁移（建表）
2. Auth 模块（注册/登录/JWT）
3. Package CRUD + 搜索 API
4. Version 提交 + 状态流转
5. 扫描触发和报告存储

## 已冻结的契约（不可随意变更）

以下内容第 2 周末已冻结，后续变更需双方协商：

- `agent-package.schema.json` — 能力包元数据结构
- `scan-report.schema.json` — 扫描报告结构
- `trust-score.schema.json` — 评分结果结构
- `openapi-v0.1.yaml` — API 接口定义
- `database-er-model.md` — 数据表结构
- `constants.ts` / `constants.py` — 枚举值定义
- `install-manifest-spec.md` — CLI 安装流程
