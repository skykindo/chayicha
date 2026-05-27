# 数据库迁移指南 — 标准资产池三层架构

## ⚠️ 重要提示

本次迁移会 **删除** 旧表 `TargetItem`、`PriceHistory`，并创建：

- `StandardAsset` — 标准资产池
- `AssetChannel` — 各平台渠道配置
- `PriceStream` — 多平台价格流水

若旧表有数据，请先导出备份（Supabase Table Editor → Export CSV）。

---

## 步骤 1：同步 Schema 到 Supabase

在项目根目录执行：

```cmd
cd d:\WorkSpace\APP002
npm run db:generate
npm run db:push
```

成功后会看到：

```
Your database is now in sync with your Prisma schema.
```

然后在 Supabase **Table Editor** 确认三张新表已出现。

> 若 `db:push` 提示 destructive change，输入 `y` 确认（开发阶段正常）。

---

## 步骤 2：插入示例数据

### StandardAsset（标准资产）

| 字段 | 示例 | 说明 |
|------|------|------|
| id | **留空** | 数据库自动生成 UUID，Supabase 不必手填 |
| name | 奇树 | 卡牌名称 |
| category | PTCG（默认）/ OPCG | 卡牌品类 |
| language | `JA` / `ZH` / `EN` | 日版 / 简中 / 英文 |
| series | M2a | 系列代号 |
| cardNumber | 246/193 | 盒内编号 |
| rarity | SAR | 罕度（SAR/AR/SR/RR 等） |
| gradingCompany | RAW / PSA / CGC / BGS / OTHER | 评级公司；裸卡选 `RAW` |
| gradeScore | 10 / 9 / 黑金10 / 金10 | 分数；裸卡留空 |
| isMonitoring | true | 是否监控 |

**评级监控建议：** 同一卡牌不同评级 = **多条 StandardAsset**（如 mega快龙 PSA10、mega快龙 PSA9、mega快龙 裸卡 各一条）。

**录入示例：**

| name | language | series | cardNumber | rarity |
|------|----------|--------|------------|--------|
| 奇树 | JA | M2a | 246/193 | SAR |

### AssetChannel（渠道 — 每张卡 × 每个平台 1 条）

| 字段 | 是否手填 | 含义 |
|------|----------|------|
| id | **留空** | 主键 UUID，数据库自动生成 |
| assetId | **必填** | 关联的 StandardAsset.id（从上一张表复制 UUID） |
| platform | **必填** | 去哪个平台抓价：`JIHUANSHE` 集换社 / `POKECOLOR` 卡乐 / `KATAO` 卡淘 |
| trackType | **必填** | 抓取方式：`WEB` 网页爬虫 / `VISION_AI` AI 视觉（集换社 Phase 2） |
| sourceUrl | 看 trackType | **直售/成交列表**；卡乐 turnover 页走 API（如 `…/turnover/index?id=239864`） |
| sourceUrlAuction | 可选 | **WEB 拍卖列表**：与直售不同页时填（如卡乐 h5 首页竞价区） |
| searchKeyword | 建议填 | 列表标题匹配词；`VISION_AI` 轨将来用作搜索词；留空则用 StandardAsset 字段自动匹配 |
| createdAt | **留空** | 创建时间，数据库自动生成（Supabase 若仍标红，见下方说明） |

> **Supabase 表编辑器提示：** `id` / `createdAt` 在数据库层已有默认值（`gen_random_uuid()` / `CURRENT_TIMESTAMP`），**不必手填**。若界面仍提示必填无法保存：硬刷新（Ctrl+F5）后重试；或在 `id` 框粘贴任意 UUID；或改用 SQL Editor 插入（见下）。

**SQL 插入示例（跳过 id / createdAt）：**

```sql
INSERT INTO "AssetChannel" ("assetId", platform, "trackType", "sourceUrl", "sourceUrlAuction", "searchKeyword")
VALUES (
  '你的-StandardAsset-uuid',
  'POKECOLOR',
  'WEB',
  'https://pokecolor.cn/h5/pages-collection/turnover/index?id=351336',
  'https://pokecolor.cn/h5/',
  'mega快龙'
);
```

**同一平台直售 + 拍卖（如 mega 快龙 @ 卡乐）：**

只需 **1 条** `AssetChannel`（`platform=POKECOLOR`）。卡乐直售与拍卖**不在同一列表页**时：

| 字段 | 填什么 |
|------|--------|
| sourceUrl | 直售页，如 [超级快龙 turnover id=239864](https://pokecolor.cn/h5/pages-collection/turnover/index?id=239864) |
| sourceUrlAuction | 拍卖页，如 [h5 竞价首页](https://pokecolor.cn/h5/) |
| searchKeyword | `mega快龙`（标题匹配建议填） |

爬虫会分别访问两页，写入 `POKECOLOR_FLOOR` 与 `POKECOLOR_AUCTION` 两条 `PriceStream`。

**滚动 / 加载更多：** 爬虫会先自动滚动页面并多次尝试点击「加载更多」，但 H5 无限滚动无法保证 100% 拉全；首屏之后的条目取决于页面是否渲染进 DOM。

**按平台怎么填：**

| platform | trackType | sourceUrl | sourceUrlAuction | searchKeyword |
|----------|-----------|-----------|------------------|---------------|
| JIHUANSHE | VISION_AI | 留空 | 留空 | 日版奇树 SAR |
| POKECOLOR | WEB | [直售 turnover](https://pokecolor.cn/h5/pages-collection/turnover/index?id=351336) | [拍卖 h5 首页](https://pokecolor.cn/h5/) | mega快龙 |
| KATAO | WEB | 卡淘搜索/已结标列表页 URL | 留空 | 奇树 PSA10（可选） |

`@@unique([assetId, platform])` — 同一标准资产在每个平台只能一条渠道。

---

## 步骤 3：运行爬虫

```cmd
npm run scraper
```

日志应显示按 `StandardAsset → AssetChannel` 分发，匹配到的成交写入 `PriceStream`。

---

## 步骤 4：查看看板

```cmd
npm run dev
```

打开 http://localhost:3000/dashboard — 多平台多线对比 + 均值线 `avg`。

---

## 可选：使用 migrate 代替 push（生产推荐）

```cmd
npm run db:migrate
```

首次会提示输入迁移名，例如：`standard_asset_pool`。

---

## 平台 / 交易类型枚举（字符串）

| 字段 | 取值 |
|------|------|
| platform | JIHUANSHE（集换社）/ POKECOLOR（卡乐）/ KATAO（卡淘） |
| trackType | WEB（网页爬虫）/ VISION_AI（AI 视觉） |
| tradeType | AUCTION / FLOOR |
