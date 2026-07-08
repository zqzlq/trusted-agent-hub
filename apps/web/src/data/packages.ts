export interface Owner {
  id: string;
  username: string;
  display_name: string;
  role: string;
}

export interface Package {
  id: string;
  name: string;
  description: string;
  type: 'skill' | 'mcp_server' | 'plugin' | 'subagent' | 'command' | 'prompt';
  license: string;
  keywords: string[];
  category: string;
  homepage: string | null;
  icon_url: string | null;
  owner: Owner;
  latest_version: string;
  status: string;
  trust_score: number | null;
  risk_level: string | null;
  install_count: number;
  avg_rating: number | null;
  created_at: string;
  updated_at: string;
}

export const packages: Package[] = [
  {
    id: 'pkg-001',
    name: 'code-review-skill',
    description: '对 Pull Request 执行多维度代码审查，覆盖正确性、安全性、性能和可维护性',
    type: 'skill',
    license: 'MIT',
    keywords: ['code-review', 'pull-request', 'quality', 'security'],
    category: 'code-generation',
    homepage: 'https://github.com/alice-dev/code-review-skill',
    icon_url: null,
    owner: { id: 'usr-001', username: 'alice', display_name: 'Alice', role: 'submitter' },
    latest_version: '1.0.0',
    status: 'published',
    trust_score: 92,
    risk_level: 'trusted',
    install_count: 1280,
    avg_rating: 4.7,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-20T14:00:00Z',
  },
  {
    id: 'pkg-002',
    name: 'postgres-explorer',
    description: 'PostgreSQL 数据库浏览与查询 MCP Server，支持只读查询、Schema 浏览和慢查询分析',
    type: 'mcp_server',
    license: 'Apache-2.0',
    keywords: ['postgresql', 'database', 'sql', 'mcp', 'read-only'],
    category: 'data',
    homepage: 'https://datatools.dev/postgres-explorer',
    icon_url: null,
    owner: { id: 'usr-002', username: 'datatools', display_name: 'DataTools Org', role: 'submitter' },
    latest_version: '2.1.0',
    status: 'published',
    trust_score: 85,
    risk_level: 'low_risk',
    install_count: 3450,
    avg_rating: 4.5,
    created_at: '2026-05-15T08:00:00Z',
    updated_at: '2026-06-15T08:00:00Z',
  },
  {
    id: 'pkg-003',
    name: 'dev-toolkit-plugin',
    description: '开发者工具箱插件，聚合代码审查 Skill、Git 命令、PR 管理 Agent',
    type: 'plugin',
    license: 'MIT',
    keywords: ['dev-tools', 'code-review', 'git', 'pr', 'productivity'],
    category: 'productivity',
    homepage: 'https://devtools.io/toolkit',
    icon_url: null,
    owner: { id: 'usr-003', username: 'devtools', display_name: 'DevTools Community', role: 'submitter' },
    latest_version: '1.3.0',
    status: 'published',
    trust_score: 78,
    risk_level: 'medium_risk',
    install_count: 892,
    avg_rating: 4.2,
    created_at: '2026-05-01T12:00:00Z',
    updated_at: '2026-06-20T14:00:00Z',
  },
  {
    id: 'pkg-004',
    name: 'demo-filesystem',
    description: '本地文件系统只读浏览 MCP Server，仅支持列出目录和读取文本文件，无写入权限',
    type: 'mcp_server',
    license: 'MIT',
    keywords: ['filesystem', 'read-only', 'mcp', 'file-browser'],
    category: 'data',
    homepage: 'https://github.com/example/demo-filesystem',
    icon_url: null,
    owner: { id: 'usr-004', username: 'demo', display_name: 'Demo User', role: 'submitter' },
    latest_version: '1.0.0',
    status: 'published',
    trust_score: 65,
    risk_level: 'medium_risk',
    install_count: 450,
    avg_rating: 3.8,
    created_at: '2026-06-10T09:00:00Z',
    updated_at: '2026-06-18T11:00:00Z',
  },
  {
    id: 'pkg-005',
    name: 'risky-executor',
    description: '声称自动优化项目性能，含危险命令、凭据读取和远程代码执行，仅供扫描器测试',
    type: 'skill',
    license: 'UNLICENSED',
    keywords: ['optimization', 'performance'],
    category: 'devops',
    homepage: null,
    icon_url: null,
    owner: { id: 'usr-005', username: 'unknown', display_name: 'Unknown Dev', role: 'submitter' },
    latest_version: '0.1.0',
    status: 'rejected',
    trust_score: 8,
    risk_level: 'untrusted',
    install_count: 0,
    avg_rating: 1.0,
    created_at: '2026-06-25T00:00:00Z',
    updated_at: '2026-06-26T00:00:00Z',
  },
  {
    id: 'pkg-006',
    name: 'git-helper-skill',
    description: 'Git 操作辅助 Skill，提供常用 Git 命令的智能封装和分支管理',
    type: 'skill',
    license: 'MIT',
    keywords: ['git', 'branch', 'commit', 'helper'],
    category: 'devops',
    homepage: 'https://github.com/example/git-helper',
    icon_url: null,
    owner: { id: 'usr-001', username: 'alice', display_name: 'Alice', role: 'submitter' },
    latest_version: '1.0.0',
    status: 'published',
    trust_score: 90,
    risk_level: 'trusted',
    install_count: 2100,
    avg_rating: 4.6,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-22T16:00:00Z',
  },
  {
    id: 'pkg-007',
    name: 'web-scraper-mcp',
    description: '网页内容抓取 MCP Server，支持 HTML 解析和结构化数据提取',
    type: 'mcp_server',
    license: 'MIT',
    keywords: ['web', 'scraper', 'html', 'data-extraction'],
    category: 'data',
    homepage: 'https://github.com/example/web-scraper-mcp',
    icon_url: null,
    owner: { id: 'usr-002', username: 'datatools', display_name: 'DataTools Org', role: 'submitter' },
    latest_version: '1.2.0',
    status: 'pending_review',
    trust_score: null,
    risk_level: null,
    install_count: 0,
    avg_rating: null,
    created_at: '2026-06-28T09:00:00Z',
    updated_at: '2026-06-28T09:00:00Z',
  },
  {
    id: 'pkg-008',
    name: 'docker-deploy-command',
    description: '一键 Docker 部署命令，封装 docker-compose 和容器管理操作',
    type: 'command',
    license: 'MIT',
    keywords: ['docker', 'deploy', 'container', 'devops'],
    category: 'devops',
    homepage: null,
    icon_url: null,
    owner: { id: 'usr-003', username: 'devtools', display_name: 'DevTools Community', role: 'submitter' },
    latest_version: '1.0.0',
    status: 'published',
    trust_score: 72,
    risk_level: 'medium_risk',
    install_count: 560,
    avg_rating: 4.0,
    created_at: '2026-06-15T10:00:00Z',
    updated_at: '2026-06-25T12:00:00Z',
  },
];
