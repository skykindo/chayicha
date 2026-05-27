# 万物皆可K线 — 项目目录说明

```
APP002/
├── apps/
│   ├── web/                    # 展示层：Next.js App Router 看板
│   │   ├── src/
│   │   │   ├── app/            # 路由（/ 首页、/dashboard 看板）
│   │   │   ├── components/     # UI 组件（charts/、ui/ shadcn）
│   │   │   └── lib/            # db.ts、utils.ts
│   │   └── components.json     # shadcn/ui 配置（待 npx shadcn@latest init）
│   └── scraper/                # 抓取层：Playwright 单线程爬虫
│       └── src/
│           ├── index.ts        # 入口
│           ├── browser.ts      # 无头浏览器 + 媒体拦截
│           ├── queue.ts        # 单线程队列
│           ├── upsert.ts       # 天级 Upsert 去重
│           └── platforms/      # 各平台解析器（集换社、卡淘…）
├── packages/
│   └── db/                     # 共享数据层：Prisma + PostgreSQL
│       ├── prisma/schema.prisma
│       └── src/index.ts        # 导出 prisma client
├── .env.example                # 环境变量模板（复制为根目录 .env）
├── package.json                # monorepo 根脚本
└── readme.md                   # 产品策划案
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置 Supabase 环境变量

复制 `.env.example` 为根目录 `.env`，填入 Supabase 控制台中的值（见下方说明）。

> Next.js 需额外复制一份：`copy .env apps\web\.env.local`（Mac/Linux: `cp .env apps/web/.env.local`）

### 3. 推送数据库 Schema

```bash
npm run db:push
```

### 4. 启动前端

```bash
npm run dev
```

访问 http://localhost:3000

### 5. 运行爬虫（Phase 1）

```bash
npm run scraper
```

## Supabase 环境变量获取指南

| 变量名 | 从哪里复制 | 用途 |
|--------|-----------|------|
| `DATABASE_URL` | Dashboard → **Project Settings → Database → Connection string → Transaction pooler → URI**（端口 **6543**，末尾加 `?pgbouncer=true`） | Next.js / Vercel 运行时查询 |
| `DIRECT_URL` | Dashboard → **Connect → Direct connection → URI**（端口 **5432**） | Prisma migrate / db push / 本地爬虫写入 |
| `NEXT_PUBLIC_SUPABASE_URL` | Dashboard → **Project Settings → API → Project URL** | 前端 Supabase Client（Phase 2+） |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Dashboard → **Project Settings → API → anon public** | 前端只读访问 |
| `SUPABASE_SERVICE_ROLE_KEY` | Dashboard → **Project Settings → API → service_role**（⚠️ 仅服务端，勿泄露） | 服务端管理操作 |

> **密码**：Database 连接串中的 `[YOUR-PASSWORD]` 是创建项目时设置的数据库密码。如忘记，可在 Database Settings 中 Reset database password。

## 常用命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动 Next.js 开发服务器 |
| `npm run db:push` | 将 Prisma Schema 同步到 Supabase |
| `npm run db:studio` | 打开 Prisma Studio 可视化管理数据 |
| `npm run scraper` | 运行 Playwright 爬虫 |
| `npm run scraper:dev` | 爬虫热重载开发模式 |

## 开发阶段

- **Phase 1（当前）**：Supabase + Playwright Upsert，实现各平台价格解析器
- **Phase 2**：Vercel 部署 + Recharts K 线看板完善 + shadcn/ui 组件
- **Phase 3**：开机自启 + Coze/Webhook 跌破阈值微信报警
