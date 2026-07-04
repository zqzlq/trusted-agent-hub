# Mock 数据说明

本目录包含前端和 CLI 开发阶段使用的 mock 数据。当后端 API 尚未就绪时，Web 和 CLI 均可直接读取这些 JSON 文件进行开发和联调。

## 目录结构

```
mock/
├── packages.json                           # 能力包列表（8 个，覆盖所有状态和类型）
└── versions/
    ├── code-review-skill-1.0.0.json        # 高可信 Skill 完整详情
    └── risky-executor-0.1.0.json           # 高风险 Skill 完整详情
```

## 使用方式

### Web (Next.js) 开发

```typescript
// 在 API route 或 getStaticProps 中
import packages from '@/packages/schema/mock/packages.json';
import versionDetail from '@/packages/schema/mock/versions/code-review-skill-1.0.0.json';

// 搜索/列表接口 mock
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q')?.toLowerCase();

  let items = packages;
  if (q) {
    items = packages.filter(p =>
      p.name.includes(q) || p.description.includes(q)
    );
  }

  return Response.json({ items, total: items.length });
}
```

### CLI 开发

```typescript
// 从本地 mock 数据读取
import * as fs from 'fs';
import * as path from 'path';

const mockDir = path.join(__dirname, '../../packages/schema/mock');
const packages = JSON.parse(
  fs.readFileSync(path.join(mockDir, 'packages.json'), 'utf-8')
);

// 搜索命令
function searchPackages(keyword: string) {
  return packages.filter(p =>
    p.name.includes(keyword) || p.description.includes(keyword)
  );
}
```

## mock 数据覆盖

| 数据 | 数量 | 覆盖内容 |
|------|------|---------|
| 已发布 Skill | 2 | code-review-skill (92分), git-helper-skill (90分) |
| 已发布 MCP Server | 2 | postgres-explorer (85分), demo-filesystem (65分) |
| 已发布 Plugin | 1 | dev-toolkit-plugin (78分) |
| 已发布 Command | 1 | docker-deploy-command (72分) |
| 待审核 | 1 | web-scraper-mcp |
| 已驳回 | 1 | risky-executor (8分) |

## 切换到真实 API

当后端就绪后，只需修改 API base URL：

```typescript
// 从 mock 切换
// const API_BASE = '';  // mock
const API_BASE = 'http://localhost:8000/api/v0';  // real API
```
