/**
 * 本地调试：测试列表页 URL 能否扫描到匹配条目
 *
 * 用法:
 *   npm run test:url -- "https://www.cardhobby.com.cn/..." "奇树 PSA10"
 */
import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { AssetCategory, Platform, TrackType } from "@everyasset/db";
import { launchBrowser } from "./browser.js";
import { scrapeKataoList } from "./platforms/katao/list-scraper.js";
import { scrapePokecolorList } from "./platforms/pokecolor/list-scraper.js";

config({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../../../.env") });

const listUrl = process.argv[2];
const keyword = process.argv[3] ?? "测试资产";

if (!listUrl) {
  console.error('用法: npm run scraper:test -- "<列表页URL>" "匹配关键词"');
  process.exit(1);
}

const mockAsset = {
  id: "test",
  assetKey: "test-asset",
  name: keyword,
  category: AssetCategory.PTCG,
  language: null,
  year: null,
  series: null,
  cardNumber: null,
  rarity: null,
  imageUrl: null,
  isMonitoring: true,
  createdAt: new Date(),
};

const mockChannel = {
  id: "test-ch",
  assetKey: "test-asset",
  platform: listUrl.includes("pokecolor") ? Platform.POKECOLOR : Platform.KATAO,
  trackType: TrackType.WEB,
  sourceUrl: listUrl,
  sourceUrlAuction: null,
  searchKeyword: keyword,
  createdAt: new Date(),
};

async function main() {
  const browser = await launchBrowser();
  const ctx = await browser.newContext({ locale: "zh-CN" });
  const page = await ctx.newPage();

  try {
    const items =
      mockChannel.platform === Platform.POKECOLOR
        ? await scrapePokecolorList(page, mockChannel, mockAsset)
        : await scrapeKataoList(page, mockChannel, mockAsset);

    console.log(`\n匹配 ${items.length} 条:`);
    console.log(JSON.stringify(items, null, 2));
  } finally {
    await page.close();
    await ctx.close();
    await browser.close();
  }
}

main().catch(console.error);
