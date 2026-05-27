import type { Page } from "playwright";
import type { StandardAsset, AssetChannel } from "@everyasset/db";
import { matchesAsset } from "../../utils/match-asset.js";
import { parseMoney } from "../../utils/parse-price.js";
import type { ListItem } from "../types.js";

/**
 * 卡淘列表/搜索/已结标页扫描
 * sourceUrl 示例：店铺成交列表、搜索「奇树 SAR」结果页等
 */
export async function scrapeKataoList(
  page: Page,
  channel: AssetChannel,
  asset: StandardAsset,
): Promise<ListItem[]> {
  if (!channel.sourceUrl) return [];

  await page.goto(channel.sourceUrl, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForTimeout(2000);

  const bodyText = await page.locator("body").innerText();
  const items: ListItem[] = [];

  // 模式 A：结标/成交  标题 ... 成交价 1234.56
  const auctionPattern =
    /([^\n]{8,120}?)\s+(?:结标|成交(?:价)?|当前价)\s*[：:\s]*([¥￥$]?\s*[\d,]+(?:\.\d+)?)/gi;
  for (const match of bodyText.matchAll(auctionPattern)) {
    const title = match[1].trim();
    const price = parseMoney(match[2]);
    if (price == null || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    items.push({
      title,
      price,
      tradeType: "AUCTION",
      info: `[KATAO] ${title.slice(0, 80)}`,
    });
  }

  // 模式 B：一口价列表  标题 ... 一口价 1,888,888.00
  const floorPattern =
    /([^\n]{8,120}?)\s+一口价\s*[：:\t\s]*([¥￥$]?\s*[\d,]+(?:\.\d+)?)/gi;
  for (const match of bodyText.matchAll(floorPattern)) {
    const title = match[1].trim();
    const price = parseMoney(match[2]);
    if (price == null || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    items.push({
      title,
      price,
      tradeType: "FLOOR",
      info: `[KATAO] ${title.slice(0, 80)}`,
    });
  }

  // 模式 C：商品链接块 — 从 item 链接附近抓标题+价
  const links = await page.locator('a[href*="/market/item/"]').all();
  for (const link of links.slice(0, 80)) {
    const title = (await link.innerText()).trim();
    if (!title || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    const rowText = await link.evaluate((el) => {
      let node: HTMLElement | null = el.closest("li, tr, div") as HTMLElement | null;
      return node?.innerText ?? el.parentElement?.innerText ?? "";
    });
    const price =
      parseMoney(rowText.match(/一口价[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "") ??
      parseMoney(rowText.match(/(?:结标|成交(?:价)?)[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "") ??
      parseMoney(rowText.match(/当前价[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "");
    if (price == null) continue;

    const tradeType: ListItem["tradeType"] = /一口价/.test(rowText)
      ? "FLOOR"
      : "AUCTION";

    items.push({
      title,
      price,
      tradeType,
      info: `[KATAO] ${title.slice(0, 80)}`,
    });
  }

  return dedupeItems(items);
}

function dedupeItems(items: ListItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.tradeType}:${item.price}:${item.title.slice(0, 40)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
