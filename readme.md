# Project: "万物皆可K线" (EveryAsset-KLine) - 混合动力双轨版

## 1. 项目愿景与痛点 (PM Vision)
本项目是一个跨品类的通用资产标的价格监控系统。
长线佛系投资策略：监控二级市场，捕捉散户恐慌踩踏时的“黄金抄底期”。
由于国内各平台筑起“流量围墙”，反爬与封闭程度不一，项目采用【双轨制混合架构】进行降维打击。

## 2. 双轨制运行逻辑 (Dual-Track Architecture)
* 【轨道 A：阳光网页爬虫流】（针对：千岛 App、卡淘、得物、Yahoo拍卖等）
    * 逻辑：在 Supabase 配置标准的 `targetUrl`。本地脚本启动 Playwright 无头浏览器，拦截多媒体资源，直接高效率解析 HTML 提取价格。
* 【轨道 B：AI视觉外挂流】（针对：集换社、闲鱼等全面封闭 Web 端的 App/小程序）
    * 逻辑：在 Supabase 配置 `searchKeyword`。本地老笔记本运行自动化脚本（如 Python PyAutoGUI），模拟真人打开电脑端微信小程序，搜索输入 -> 定点截图 -> 将图片发给 Gemini 1.5 Flash 视觉接口看图读数。

无论走哪条轨道，最终清洗出来的【最低挂牌价】与【最新成交价】数据结构完全一致，统一无缝汇入云端。

## 3. 技术栈选型 (Tech Stack)
* 前端展示：Next.js 14+ (App Router) + Tailwind CSS + shadcn/ui + Recharts (K线渲染)
* 云数据库：Supabase (PostgreSQL) + Prisma ORM
* 本地自动化：Node.js + Playwright (轨道A) / Python (轨道B: PyAutoGUI + Pillow)
* 视觉大脑：Google Generative AI SDK (Gemini 1.5 Flash API - 每日1500次免费额度)

## 4. 终极统一数据库模型 (Prisma Schema)
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model TargetItem {
  id             String         @id @default(uuid())
  name           String         // 商品名称 (如: 日版奇树 SAR / 2003年梅西新秀卡)
  category       String         // 行业分类: PTCG / SPORTS_CARD / TOY
  trackType      String         // 核心轨道标记: WEB(走网页爬虫) / VISION(走AI视觉)
  targetUrl      String?        // 轨道A专属：千岛/卡淘的网页公开URL
  searchKeyword  String?        // 轨道B专属：微信小程序/闲鱼的精准搜索词
  isMonitoring   Boolean        @default(true)
  createdAt      DateTime       @default(now())
  prices         PriceHistory[]
}

model PriceHistory {
  id             String         @id @default(uuid())
  targetId       String
  target         TargetItem     @relation(fields: [targetId], references: [id], onDelete: Cascade)
  minFloorPrice  Float          // 挂牌市场/屏幕首选的地板价（看散户恐慌割肉）
  lastSoldPrice  Float          // 挂牌或拍卖的最新一笔真实成交价（如果当天没成交，沿用上一日）
  auctionPrice   Float?         // 备用：针对卡淘纯拍卖结标价
  capturedAt     DateTime       @default(now()) // 抓取时间（天级）
  
  @@unique([targetId, capturedAt]) // 联合唯一索引：多端/多电脑重复跑时天级自动去重覆写
}
##5. 当前开发任务（MVP 骨骼构建）
👉 当前任务：请作为全栈架构师，阅读并理解本策划案。请帮我：

生成标准的 Next.js 14+ 项目目录结构。

生成 schema.prisma 文件，并指导我如何在本地通过 .env 连接到我的 Supabase。

帮我编写一段本地脚本的分发逻辑：如何读取 TargetItem，当 trackType === 'WEB' 时调用网页抓取函数，当 trackType === 'VISION' 时调用本地自动化函数。

---

## 6. 代码已同步（标准资产池三层架构）

| 层 | 模型 | 说明 |
|----|------|------|
| 标准池 | `StandardAsset` | 含 category(PTCG/OPCG) / language / series / cardNumber / rarity |
| 渠道 | `AssetChannel` | JIHUANSHE/POKECOLOR/KATAO + WEB/VISION_AI |
| 流水 | `PriceStream` | 多平台多交易类型天级去重 |

迁移步骤见 [docs/MIGRATION.md](./docs/MIGRATION.md)。