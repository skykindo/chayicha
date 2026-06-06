# npm 常用指令速查

> 在项目根目录 `D:\WorkSpace\APP002` 执行。  
> 带 `--` 的是把参数传给底层脚本，例如：`npm run vision:import -- --sync`  
> **不要**在 Supabase 表编辑器里改 `AssetChannel` / `StandardAsset`，用下方 CSV + import 命令。

---

## 一、三个 CSV 文件（各管一层）

| 文件 | 管什么 | 导入命令 | 导出命令 |
|------|--------|----------|----------|
| `卡牌-import.csv` | 标准资产 `StandardAsset`（名称、series、编号等） | `npx tsx scripts/import-standard-assets.ts` | — |
| `web-channels.csv` | **路线 A** WEB 爬虫（卡乐 POKECOLOR 等） | `npm run web:import` | `npm run web:export` |
| `vision-channels.csv` | **路线 B** 集换社 VISION | `npm run vision:import` | `npm run vision:export` |

同一 `assetKey` **可以同时**出现在 `web-channels.csv` 和 `vision-channels.csv`（平台不同：`POKECOLOR` vs `JIHUANSHE`）。

**旧文件（不必再用）：** `渠道-import.csv` → 用 `npm run web:export` 生成 `web-channels.csv`；`卡牌vision渠道.csv` → 已合并到 `vision-channels.csv`。

---

## 二、CSV 列说明

### 卡牌-import.csv

| 字段 | 说明 |
|------|------|
| `assetKey` | 业务主键，全局唯一 |
| `name` / `category` / `series` / `cardNumber` / … | 见 `卡牌-import.csv` 表头 |
| `isMonitoring` | `true` 才参与爬虫与首页 |

### web-channels.csv（6 列）

```csv
assetKey,trackType,platform,sourceUrl,sourceUrlAuction,searchKeyword
PTCG-JA-s8a-p-001/025-Promo,WEB,POKECOLOR,https://pokecolor.cn/h5/pages-collection/turnover/index?id=15863,,
```

| 字段 | 填法 |
|------|------|
| `assetKey` | 必填，须已在 `卡牌-import.csv` |
| `trackType` | 固定 `WEB` |
| `platform` | `POKECOLOR` / `KATAO` 等 |
| `sourceUrl` | 卡乐 turnover 页 URL（必填） |
| `sourceUrlAuction` | 拍卖列表页（可选） |
| `searchKeyword` | 标题匹配词（可选） |

### vision-channels.csv（7 列，心愿单模式建议带 gridSlot）

```csv
assetKey,trackType,platform,sourceUrl,sourceUrlAuction,searchKeyword,gridSlot
PTCG-JA-s8a-p-010/025-Promo,VISION,JIHUANSHE,,,,1
```

| 字段 | 填法 |
|------|------|
| `gridSlot` | **心愿单专用**：该卡在 4×3 网格中的位置 **1～12**（`grid_01`～`grid_12`）。**与 CSV 第几行无关**；心愿单增删卡后只改 `gridSlot` + 坐标，行顺序可乱 |

**心愿单维护（不必与 CSV 行序一致）：**

1. 在 App 心愿单里增删卡后，看每张卡在第几格（左上=1，向右递增，换行继续）。
2. 在 CSV 为该 `assetKey` 填写对应 `gridSlot`；新卡加一行，删卡删行后 `npm run vision:import -- --sync`。
3. `npm run vision:list` 核对「卡名 ↔ grid_0N」是否与屏幕一致。
4. `layout.json` 的 `grid_01`～`grid_12` 是屏幕坐标，与 `gridSlot` 数字对应，不随 CSV 行移动。
| `assetKey` | 必填，须已在 `卡牌-import.csv` |
| `trackType` | 固定 `VISION` |
| `platform` | 固定 `JIHUANSHE` |
| `sourceUrl` / `sourceUrlAuction` | 留空 |
| `searchKeyword` | 通常留空；RPA 搜卡靠 `StandardAsset.series` + `cardNumber` |

---

## 三、CSV 导入命令详解

### 标准资产

```powershell
npx tsx scripts/import-standard-assets.ts
npx tsx scripts/import-standard-assets.ts 其他.csv
```

- **Upsert**：CSV 里有的 `assetKey` → 更新字段；**不会删除** CSV 里没有的卡。
- **PriceStream 不受影响**。

### WEB 渠道

```powershell
npm run web:import                      # 只增/改 CSV 中的行
npm run web:import -- --sync            # 增/改 + 删除 CSV 中已去掉的 WEB 渠道
npm run web:import -- --dry-run         # 只校验，不写库
npm run web:export                      # 数据库 → web-channels.csv
```

### VISION 渠道

```powershell
npm run vision:import
npm run vision:import -- --sync
npm run vision:import -- --dry-run
npm run vision:export
npm run vision:list                     # 列出将采集的 VISION 渠道（不写库）
```

- `--sync` 只删 **对应轨道** 的渠道：`web:import --sync` 只动 `trackType=WEB`；`vision:import --sync` 只动 `VISION + JIHUANSHE`。
- **同一 assetKey 的 WEB 与 VISION 互不影响**（平台不同）。

---

## 四、重新上传 CSV 会发生什么？

**PriceStream（历史价格）在任何 import 下都不会被删除。**

### 场景：第一天 100 行已 import，第二天 CSV 剩 51 行（删 50 + 新 1）

| 操作 | WEB 渠道库内条数 | VISION 渠道库内条数 | PriceStream |
|------|------------------|---------------------|-------------|
| 第一天 `import` 100 行 | 100 | 100 | 不变 |
| 第二天 51 行，**不加 `--sync`** | **101**（50 条孤儿 + 51 更新/新建） | **101** | 不变 |
| 第二天 51 行，**加 `--sync`** | **51** | **51** | 仍保留 |

### 一般规则

| 导入方式 | 会影响 | 不会影响 |
|----------|--------|----------|
| `import-standard-assets` | CSV 内卡的字段更新 | 删不掉 CSV 外的卡；PriceStream |
| `web:import` / `vision:import`（无 sync） | CSV 内渠道 upsert | CSV 外渠道仍留在库；PriceStream |
| `web:import -- --sync` | 还会删 CSV 没有的 **WEB** 渠道 | PriceStream；VISION 渠道 |
| `vision:import -- --sync` | 还会删 CSV 没有的 **VISION** 渠道 | PriceStream；WEB 渠道 |
| Supabase 网页直接导 CSV | **不推荐**，易冲突 | — |

### 建议习惯

- **日常只增改**：不加 `--sync`。
- **CSV 删行且要从库删掉**：加 `--sync`。
- **改前先备份**（可选）：`npm run web:export` / `npm run vision:export`。
- 重传**相同内容**：安全，相当于覆盖更新。

---

## 五、常见操作

### 新加几张卡，只要 VISION

```powershell
# 1. 编辑 卡牌-import.csv → 导入标准资产
npx tsx scripts/import-standard-assets.ts
# 2. 编辑 vision-channels.csv → 导入渠道
npm run vision:import
npm run vision:list
```

### 新加几张卡，只要 WEB

```powershell
npx tsx scripts/import-standard-assets.ts
# 编辑 web-channels.csv（含 sourceUrl）
npm run web:import
```

### 同一张卡 WEB + VISION 都要

两个 CSV **各加一行** → 分别 `npm run web:import` 和 `npm run vision:import`（顺序不限）。

### 只改 VISION、不动 WEB

只编辑 `vision-channels.csv`，只跑 `npm run vision:import`。

---

## 六、前端 Web

| 指令 | 说明 |
|------|------|
| `npm run dev` | 启动 Next.js 开发服务器（首页 / 散点图） |
| `npm run build` | 生产构建 |

---

## 七、数据库（Prisma / Supabase）

| 指令 | 说明 |
|------|------|
| `npm run db:generate` | 改 schema 后生成 Prisma Client（若 EPERM，先停 dev/scraper） |
| `npm run db:push` | 把 schema 推到 Supabase |
| `npm run db:migrate` | 创建/执行迁移 |
| `npm run db:studio` | 打开 Prisma Studio 查表 |

---

## 八、路线 A：WEB 爬虫（卡乐 Playwright）

| 指令 | 说明 |
|------|------|
| `npm run scraper` | **跑一轮** → 写 `PriceStream`，跑完退出；**支持断点续跑** |
| `npm run scraper -- --reset-checkpoint` | 清空断点，从第 1 张全量重跑 |
| `npm run scraper:progress` | 卡乐流水覆盖进度（累计多少张有数据；**非本轮进度**） |
| `npm run scraper:dev` | `tsx watch` 常驻；改代码会重跑整轮 — **日常采集不要用** |
| `npm run scraper:browser` | 首次安装 Playwright Chromium |
| `npm run scraper:test` | 单 URL 测试 |

**环境变量（`.env`）：**

| 变量 | 默认 | 说明 |
|------|------|------|
| `SCRAPER_REQUEST_DELAY_MS` | `3000` | 每卡渠道间隔（毫秒） |
| `SCRAPER_HEADLESS` | `true` | `false` 可见浏览器 |
| `SCRAPER_USE_SYSTEM_CHROME` | — | `true` 用本机 Chrome |
| `SCRAPER_START_FROM_ASSET_KEY` | — | 临时从某 assetKey 起跑（含） |

**断点续跑：** `apps/scraper/checkpoint.json`

- `startFromAssetKey`：下轮从该卡开始（含）。
- `lastCompletedAssetKey`：每完成一张自动更新；Ctrl+C 后再跑从下一张继续。
- 全部跑完 → 断点自动清空。

**耗时（实测级）：** 每张卡会拉 API 全量历史并**逐条 upsert**，热门卡可刷上百条 `[dispatch]`。479 张全量一轮常需 **数小时**；不是「479×3 秒 ≈ 25 分钟」。睡眠/休眠会暂停进程，跑时设「从不睡眠」。

**看本轮跑到哪：** 终端数 `[queue] 卡名 → POKECOLOR (WEB)` 行数，或看最后一条 `[queue]`。`scraper:progress` 看的是累计有流水的卡数（`capturedAt` 是成交日，不能用来判断本轮）。

---

## 九、路线 B：VISION 集换社（Python）

| 指令 | 说明 |
|------|------|
| `npm run vision` | 跑一轮 RPA + Gemini → 写 `PriceStream` |
| `npm run vision:list` | 列出将采集的渠道 |
| `npm run vision:import` / `export` | 见第三节 |

**Python 依赖（首次）：**

```powershell
python -m pip install -r apps/vision/requirements.txt
```

**环境变量：** `DIRECT_URL`、`GEMINI_API_KEY`；测试 `VISION_MOCK=1`、`VISION_MOCK_GEMINI=1`。

**配置：** `apps/vision/vision.config.json`（`maxLimit` 默认 50）、本机 `apps/vision/layout.json`。

```powershell
python apps/vision/main.py --reset-checkpoint
```

**规模：** 最多 50 张（`vision.config.json` → `maxLimit`），整轮约 **25～40 分钟**（与 WEB 全量不是同一量级）。

---

## 十、调试脚本

| 指令 | 说明 |
|------|------|
| `npx tsx scripts/check-db.ts` | 检查数据库连接 |
| `npx tsx scripts/check-home-query.ts` | 检查首页查询 |
| `npx tsx scripts/check-web-query.ts` | 检查 Web 端数据查询 |
| `npx tsx scripts/migrate-to-asset-key.ts` | 历史迁移（一般已跑过） |
| `npx tsx scripts/debug-page-text.ts` | 调试页面文本解析 |

---

## 十一、推荐日常流程

```powershell
# 改标准资产
# 编辑 卡牌-import.csv
npx tsx scripts/import-standard-assets.ts

# 只改 VISION 渠道
# 编辑 vision-channels.csv
npm run vision:import
npm run vision:list

# 只改 WEB 渠道
# 编辑 web-channels.csv
npm run web:import

# 卡乐抓价（每天 1～2 次；跑完即停）
npm run scraper

# 集换社 VISION（手动打开微信小程序后）
npm run vision

# 看板
npm run dev
```

---

## 十二、相关文档

- [VISION-TRACK.md](./VISION-TRACK.md) — 集换社视觉轨策划
- [MIGRATION.md](./MIGRATION.md) — 三层架构（部分 trackType 文案以 `VISION` 为准）
- [CHANNELS.md](./CHANNELS.md) — 本页摘要跳转
