# 轨道 B：集换社视觉采集策划案

> 版本：v1.0（定稿讨论稿）  
> 状态：待开发  
> 适用范围：集换社 **Android App**（推荐：安卓模拟器）或 PC 微信小程序（`JIHUANSHE` + `trackType=VISION`）  
> 代码目录：`apps/vision/`（扩展现有占位，不新建 `vision_scraper/`）

---

## 1. 背景与目标

### 1.1 项目现状

- **路线 A（WEB）** 已跑通：`StandardAsset` → `AssetChannel` → `PriceStream` → 首页列表 + 散点图。
- 卡乐（`POKECOLOR` + `WEB`）通过 turnover API 批量采集，约 478 张卡。
- 集换社、闲鱼等封闭小程序 **无稳定公开列表 URL**，需 **轨道 B**。

### 1.2 轨道 B 目标

在本地 Windows 环境，通过：

1. **RPA**（PyAutoGUI + pygetwindow）模拟真人操作集换社客户端（**推荐安卓模拟器**；PC 微信小程序功能不全，见 §4.1）；
2. **Gemini 1.5 Flash** 视觉识别列表/详情页价格；
3. **Python 直连 Supabase PostgreSQL** 写入 `PriceStream`；

使集换社价格与卡乐价格 **汇入同一张流水表、同一套看板**，支持跨平台比价与后续套利分析。

### 1.3 规模与配额

| 指标 | 数值 |
|------|------|
| VISION 监控规模 | **最多 50 张卡**（`MAX_LIMIT=50`） |
| 选型方式 | 配置 `AssetChannel` 即纳入；按 **`createdAt` 导入顺序** 取前 50 条 |
| Gemini 调用/卡/天 | 2 次（一口价 Tab + 竞价 Tab 各 1 截图） |
| Gemini 日调用上限 | ≈100 次/天（50 × 2），远低于免费档 ~1500 次/天 |
| 闲鱼 | **Phase 2 再做**，本方案仅集换社 |

---

## 2. 与现有数据模型的关系

### 2.1 三层结构（不变）

```
StandardAsset（一张卡一条，assetKey 业务主键）
    └── AssetChannel（每卡 × 每平台一条渠道）
            └── PriceStream（全平台全品相成交/挂牌流水）
```

### 2.2 路线 A vs 路线 B

| 维度 | 路线 A（WEB） | 路线 B（VISION） |
|------|---------------|------------------|
| 平台 | 卡乐、卡淘等 | 集换社（本期） |
| `trackType` | `WEB` | `VISION` |
| 入口 | `sourceUrl`（turnover 链接） | **无 URL** |
| 匹配 | 标题 token / `searchKeyword` | **RPA 导航 + 截图** |
| 评级 | `PriceStream.cardCondition` | 同左，由 Gemini / 页签语义推断 |
| 调度 | `npm run scraper`（Node） | **独立 Python 脚本**（第一期） |

同一张卡可同时拥有：

- `POKECOLOR` + `WEB`（全量或大批量）
- `JIHUANSHE` + `VISION`（subset 最多 50 张）

约束：`@@unique([assetKey, platform])`，每卡每平台仅一条渠道。

### 2.3 前端影响

- 首页 `page.tsx` 已聚合 `StandardAsset.prices`（全平台 `PriceStream`）。
- **VISION 数据写入格式正确即可，首页无需改架构。**
- **集换价**：入库收集，散点图 **MVP 默认不展示**（后续按 `info` 字段过滤）。

---

## 3. 渠道配置（AssetChannel）

### 3.1 纳入条件

脚本启动时从 Supabase 读取：

```sql
SELECT ac.*, sa.series, sa.cardNumber, sa.name
FROM "AssetChannel" ac
JOIN "StandardAsset" sa ON sa."assetKey" = ac."assetKey"
WHERE ac."trackType" = 'VISION'
  AND ac.platform = 'JIHUANSHE'
  AND sa."isMonitoring" = true
ORDER BY ac."createdAt" ASC
LIMIT 50;
```

### 3.2 字段填法

| 字段 | 集换社 VISION | 说明 |
|------|---------------|------|
| `assetKey` | **必填** | 与 `StandardAsset` 一致，入库关联键 |
| `platform` | `JIHUANSHE` | 固定 |
| `trackType` | `VISION` | 固定 |
| `sourceUrl` | 留空 | WEB 专用 |
| `sourceUrlAuction` | 留空 | WEB 专用 |
| `searchKeyword` | **可选** | 消歧用；主路径用 `series` + `cardNumber` |
| `id` / `createdAt` | 不填 | 数据库自动生成 |

### 3.2.1 推荐维护方式（本地 CSV，勿手改 Supabase）

**主文件**：根目录 `vision-channels.csv`（仅 6 列，用 Excel/VS Code 编辑即可）。

| 命令 | 作用 |
|------|------|
| `npm run vision:import` | CSV → 数据库 upsert |
| `npm run vision:import -- --sync` | 同上，并**删除 CSV 里已去掉的行** |
| `npm run vision:import -- --dry-run` | 只校验，不写库 |
| `npm run vision:export` | 数据库 → 覆盖写回 `vision-channels.csv` |
| `npm run vision:list` | 查看脚本将处理的渠道 |

**日常改渠道**：编辑 `vision-channels.csv` → `npm run vision:import -- --sync` → `npm run vision:list` 确认。

> 不要用 Supabase 表编辑器改 VISION 渠道；改完也建议 `npm run vision:export` 拉回本地，保持 CSV 与库一致。

### 3.3 安全阀门

- **集中配置**：`apps/vision/vision.config.json` → **`maxLimit`**（当前 **50**）。
- 环境变量 **`VISION_MAX_LIMIT`** 可临时覆盖（优先级高于配置文件）。
- 若符合条件的渠道 **超过 maxLimit**：只处理前 N 条（按 `createdAt ASC`），日志输出实际条数。
- **不**再使用「日常 50 / 上限 100」双档配置。

### 3.4 RPA 导航与 StandardAsset 字段

| RPA 步骤 | 使用的数据 | 示例 |
|----------|------------|------|
| 搜「卡盒」 | `StandardAsset.series` | `M2a`、`SV2a`、`s8a-p` |
| 搜「编号」 | `StandardAsset.cardNumber` | `236/193`、`001/025` |
| 入库 | `AssetChannel.assetKey` | `PTCG-JA-M2a-236/193-SAR` |
| 消歧（可选） | `AssetChannel.searchKeyword` | 同名/同编号冲突时 |

**`searchKeyword` 不是内部检索词**，是给集换社搜索 UI 用的；内部关联始终靠 `assetKey`。

---

## 4. 集换社 UI 与 RPA 流程

### 4.1 业务认知（集换社页面结构）

- 卡牌详情页有 **两个页签**：**一口价**、**竞价**（同一页面内切换）。
- **一口价页签**
  - **最低价**：当前最低挂牌。
  - **集换价**：平台统计的一段时间均价（**PSA 侧关注，需入库**）。
- **竞价页签**
  - **当前竞价**：进行中的出价。
  - **成交价**：已结束成交。
- **品相分工（不混排假设）**
  - 一口价页签：主要是 **裸卡（RAW）** 的最低价；集换价归 **PSA** 语义。
  - 竞价页签：主要是 **PSA** 的当前竞价与成交价。
- MVP **不做列表滑动**，只截当前可见区域。

### 4.1 客户端选型：模拟器 vs 微信小程序

| 客户端 | 卡盒内搜编号 | 建议 |
|--------|----------------|------|
| **PC 微信 · 集换社小程序** | 往往**没有**盒内搜卡能力，RPA 流程不完整 | 不推荐 |
| **安卓模拟器 · 集换社 App** | 有完整搜索与列表，与脚本步骤一致 | **推荐** |

模拟器环境要点（雷电 / MuMu / 夜神等均可）：

1. 安装集换社 **Android 版** APK，登录同一账号。
2. 模拟器窗口固定到屏幕 **左上角 (0, 0)**（脚本会 `moveTo(0,0)`，坐标按屏幕像素校准）。
3. `layout.json` → `windowTitleKeyword` 填 **模拟器窗口标题**里能匹配到的词，例如：
   - `雷电模拟器` / `MuMu模拟器` / `夜神模拟器`
   - 或窗口标题里出现的 `集换社`（以任务管理器/Alt+Tab 实际标题为准）
4. **整套 `points` 坐标在模拟器里重新测一遍**（与微信小程序坐标不通用）。
5. 分辨率、DPI 固定后不要改；改分辨率需重校坐标。

### 4.2 单卡完整 RPA 流程

```
[前置] 打开安卓模拟器 → 启动集换社 App（已登录）→ 停在可全局搜索的首页

对每个 AssetChannel（最多 50 条）：

  1. pygetwindow 定位模拟器/App 窗口 → 移动到 (0, 0)
  2. 全局搜索：粘贴「卡盒名」(series) → 回车 → 等待 2~3s
  3. 点击「系列」筛选按钮 (series_button) → 等待 2~3s
  4. 点击卡盒列表第一条 (box_result_first) → 进入卡盒
  5. 盒内搜索：粘贴「编号」(cardNumber) → 回车 → 等待 2~3s
  6. 点击卡牌第一条 → 进入详情页
  7. 点击「一口价」Tab → 截图 → floor.png
  8. 点击「竞价」Tab   → 截图 → auction.png
  9. Gemini 解析 → upsert PriceStream
 10. 随机休眠 6~12s → checkpoint → 下一张
```

### 4.3 人机对抗

| 措施 | 参数 |
|------|------|
| 随机休眠 | 每卡完成后 **6～12 秒** |
| 操作间隔 | 点击/搜索后 **2～3 秒** 等待加载 |
| 中文输入 | **剪贴板 + Ctrl+V**，禁止 `typewrite` 打中文 |
| 窗口归位 | 强制窗口 **(0, 0)**，配合固定 `layout.json` 坐标 |

### 4.4 坐标配置（layout.json）

路径建议：`apps/vision/layout.json`（每台采集机一份，可 gitignore 模板 + 示例）。

需配置项：

- 窗口标题关键字（匹配**模拟器窗口**或 App，见 §4.1）
- 全局搜索框坐标
- **系列筛选按钮**坐标（`series_button`，全局搜索提交后点击）
- 卡盒列表 **第一条结果**（`box_result_first`）
- 卡盒内搜索框坐标
- **一口价 Tab** / **竞价 Tab** 点击坐标
- 详情页 **截图 region** `(x, y, width, height)`
- （预留）列表滚动中心点 — MVP 不用

---

## 5. Gemini 视觉解析

### 5.1 调用策略

- 模型：**Gemini 1.5 Flash**（`google-generativeai`）。
- 每卡 **2 次调用**（或 1 次传入 2 张图，实现时择一）。
- API Key：`GEMINI_API_KEY`（`.env`）。

### 5.2 输出格式（数组，支持多价格点）

要求模型 **只输出 JSON，无 Markdown**，结构示例：

```json
{
  "items": [
    {
      "price": 520.0,
      "tradeType": "FLOOR",
      "cardCondition": "RAW",
      "priceKind": "最低价"
    },
    {
      "price": 680.0,
      "tradeType": "FLOOR",
      "cardCondition": "PSA10",
      "priceKind": "集换价"
    },
    {
      "price": 750.0,
      "tradeType": "AUCTION",
      "cardCondition": "PSA10",
      "priceKind": "当前竞价"
    },
    {
      "price": 720.0,
      "tradeType": "AUCTION",
      "cardCondition": "PSA10",
      "priceKind": "成交价"
    }
  ]
}
```

- 无法识别的字段：`price` 为 `null`，**跳过不入库**。
- 不要猜测；对不上的品相不要硬填。

### 5.3 页签与 Prompt 分工

| 截图来源 | Prompt 侧重 | 预期 `cardCondition` |
|----------|-------------|----------------------|
| 一口价 Tab | 最低价（RAW）、集换价（PSA） | `RAW` / `PSA10` |
| 竞价 Tab | 当前竞价、成交价 | `PSA10` |

---

## 6. 入库规范（PriceStream）

### 6.1 Python 写库方式

- **不使用 Prisma**（Python 无 Prisma Client）。
- 使用 **`python-dotenv` + `psycopg2`**，连接 `.env` 中 **`DIRECT_URL`**。
- 使用 **`INSERT ... ON CONFLICT DO UPDATE`**，与 Node 端 `upsertPriceStream` 对齐。

### 6.2 唯一键（与 schema 一致）

```
assetKey + platform + tradeType + price + capturedDate + cardCondition + info
```

### 6.3 字段映射

| Gemini / 业务 | `PriceStream` 字段 | 值 |
|---------------|-------------------|-----|
| 平台 | `platform` | `JIHUANSHE` |
| 关联卡 | `assetKey` | 来自 `AssetChannel` |
| 价格 | `price` | 浮点数（元） |
| 交易类型 | `tradeType` | `FLOOR`（一口价）/ `AUCTION`（竞价） |
| 品相 | `cardCondition` | `RAW` / `PSA10` / `PSA9` / `CGC10` |
| 语义区分 | `info` | 见下表 |
| 日期 | `capturedDate` | 当天 `YYYY-MM-DD` |
| 时间 | `capturedAt` | 采集时刻 |

### 6.4 `info` 固定文案（防 dedupe 冲突）

| 价格类型 | `tradeType` | `cardCondition` | `info` |
|----------|-------------|-----------------|--------|
| 最低价 | `FLOOR` | `RAW` | `[VISION] 一口价-最低价` |
| 集换价 | `FLOOR` | **`PSA10`** | `[VISION] 一口价-集换价` |
| 当前竞价 | `AUCTION` | `PSA10` | `[VISION] 竞价-当前价` |
| 成交价 | `AUCTION` | `PSA10` | `[VISION] 竞价-成交价` |

**集换价归属说明**：集换价在业务上属于 PSA 参考价，入库时 **`cardCondition` 标为 `PSA10`（或后续扩展的 PSA 档）**，**不要**标为 `RAW`。散点图 MVP 通过过滤 `info` 含「集换价」隐藏，但数据库保留用于分析。

### 6.5 一条 Gemini 结果 → 多条流水

- 每个 `items[]` 元素若 `price != null` → **insert/upsert 一行**。
- 同一卡、同一天、不同 `info` → 可多行共存。

---

## 7. 断点续爬（Checkpoint）

### 7.1 目标

网络闪断、微信弹窗、Gemini 失败时，**从中断处继续**，不从第 1 张重跑。

### 7.2 建议实现

- 状态文件：`apps/vision/checkpoint.json`（可 gitignore）。
- 记录内容：
  - 当前 `assetKey`
  - 当前步骤（如 `box_search` | `pick_series` | `enter_box` | `number_search` | `enter_card` | `shot_floor` | `shot_auction` | `db_write` | `done`）
  - 本轮开始时间、已成功/失败计数
- 重启脚本：读取 checkpoint → 跳过已完成步骤/已完成卡。

---

## 8. 工程结构（apps/vision）

```
apps/vision/
├── main.py              # 入口：读库 → RPA → Gemini → 写库
├── vision.config.json   # ★ 可调参数（maxLimit=50、休眠、等待秒数等）
├── requirements.txt
├── layout.json          # 坐标配置（本机，从 example 复制）
├── layout.example.json
├── checkpoint.json      # 运行时生成
├── screenshots/         # 调试留存 {assetKey}_floor.png / _auction.png
├── config.py            # 读 vision.config.json + .env
├── db.py                # psycopg2 upsert PriceStream
├── rpa.py               # 窗口、搜索、Tab、截图
├── gemini_client.py     # 视觉 Prompt + JSON 解析
└── checkpoint.py        # 断点续爬
```

### 8.1 与 Node 调度器关系

| 阶段 | 方式 |
|------|------|
| **第一期** | 独立运行：`python apps/vision/main.py` |
| **后续可选** | Node `runVisionChannel` spawn 同一脚本，并入 `npm run scraper` 队列 |

---

## 9. 环境变量

| 变量 | 用途 |
|------|------|
| `DIRECT_URL` | Python PostgreSQL 直连（写 `PriceStream`） |
| `GEMINI_API_KEY` | Gemini API |
| `VISION_MAX_LIMIT` | 可选，覆盖 `vision.config.json` 的 `maxLimit` |
| `VISION_MOCK` | `1` 时跳过真实 RPA（生成占位截图） |
| `VISION_MOCK_GEMINI` | `1` 时跳过 Gemini API（测试写库） |
| `VISION_PYTHON` | Node 将来 spawn 用，默认 `python` |

`.env` 与 monorepo 根目录共用。

---

## 10. 运行与测试

### 10.1 首次测试（半自动）

1. 用户在 Supabase 为 **2～3 张试点卡** 配置 `AssetChannel`（`VISION` + `JIHUANSHE`）。
2. 确认 `StandardAsset.series` / `cardNumber` 与集换社 UI 一致。
3. 校准 `layout.json` 坐标。
4. 打开安卓模拟器 → 集换社 App；校准 `layout.json`（§4.1）。
5. 运行脚本，检查：
   - `screenshots/` 截图是否正确
   - `PriceStream` 是否写入
   - 首页该卡是否出现集换社样本数

### 10.2 正式运行

1. 配置满 **≤50 条** VISION 渠道。
2. 建议 **每天 1 轮**（如晚间），耗时约 **25～40 分钟**（50 卡 × 多步 RPA + 休眠）。
3. 失败卡查看日志 + 截图，手动修正 `series`/坐标后重跑。

---

## 11. 风险与限制

| 风险 | 缓解 |
|------|------|
| 微信/集换社 UI 改版 | `layout.json` 版本化；失败截图归档 |
| 坐标因分辨率失效 | 固定窗口 (0,0) + 本机 layout |
| Gemini 误读 | 固定 Prompt；`null` 跳过；人工抽查截图 |
| 小程序风控 | 6～12s 随机休眠；单日 50 卡 |
| 卡盒/编号与库内字段不一致 | 试点校准；可选 `searchKeyword` 消歧 |
| 集换价与散点图语义混杂 | MVP 图表过滤 `info` 含集换价 |

---

## 12. 后续迭代（不在 MVP）

- [ ] 闲鱼（`IDLEFISH` + `VISION`）独立 layout 与流程
- [ ] 散点图按 `info` 过滤集换价/竞价当前价
- [ ] 列表滑动加载更多
- [ ] 接入 Node `npm run scraper` 统一调度
- [ ] PSA9、CGC10 等多档品相 Prompt
- [ ] 按 `Holding` 优先队列（先跑持仓卡）

---

## 13. 决策记录（定稿）

| # | 决策 |
|---|------|
| 1 | 只读 `AssetChannel` 且 `trackType=VISION`、`platform=JIHUANSHE` |
| 2 | 上限 **50 张**，按 `createdAt` 导入顺序 |
| 3 | RPA：**卡盒(series) → 进盒 → 编号(cardNumber) → 进卡 → 两 Tab 各截图** |
| 4 | 每卡 2 张图、2 次 Gemini；MVP 不滑动 |
| 5 | 中文剪贴板粘贴；窗口 (0,0)；`layout.json` 配坐标 |
| 6 | 入库拆多行；`info` 区分价种；集换价 `cardCondition=PSA10` |
| 7 | 集换价入库但散点图 MVP 不展示 |
| 8 | Python `psycopg2` + `DIRECT_URL` upsert |
| 9 | 代码目录 **`apps/vision/`** |
| 10 | 第一期独立 Python；测试时用户手动打开小程序 |
| 11 | 闲鱼 Phase 2 |

---

## 14. 相关文件

- 数据模型：`packages/db/prisma/schema.prisma`
- WEB 轨 upsert 参考：`apps/scraper/src/upsert.ts`
- VISION 占位：`apps/scraper/src/platforms/vision/index.ts`
- 环境变量示例：`.env.example`
- WEB 迁移说明：`docs/MIGRATION.md`
