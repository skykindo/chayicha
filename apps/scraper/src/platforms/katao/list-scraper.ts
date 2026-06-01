import type { Page } from "playwright";
import { parseCardCondition, type StandardAsset, type AssetChannel } from "@everyasset/db";
import { matchesAsset } from "../../utils/match-asset.js";
import {
  parseCapturedDateFromText,
  parseSentimentFromText,
} from "../../utils/parse-sentiment.js";
import { parseMoney } from "../../utils/parse-price.js";
import type { ListItem } from "../types.js";

/**
 * 卡淘历史成交搜索列表页 — 全量扫描最新成交条目
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

  const auctionPattern =
    /([^\n]{8,120}?)\s+(?:结标|成交(?:价)?|当前价)\s*[：:\s]*([¥￥$]?\s*[\d,]+(?:\.\d+)?)/gi;
  for (const match of bodyText.matchAll(auctionPattern)) {
    pushItem(items, match[1], match[2], "AUCTION", bodyText, asset, channel);
  }

  const floorPattern =
    /([^\n]{8,120}?)\s+一口价\s*[：:\t\s]*([¥￥$]?\s*[\d,]+(?:\.\d+)?)/gi;
  for (const match of bodyText.matchAll(floorPattern)) {
    pushItem(items, match[1], match[2], "FLOOR", bodyText, asset, channel);
  }

  const links = await page.locator('a[href*="/market/item/"]').all();
  for (const link of links.slice(0, 120)) {
    const title = (await link.innerText()).trim();
    if (!title || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    const rowText = await link.evaluate((el) => {
      const node = el.closest("li, tr, div") as HTMLElement | null;
      return node?.innerText ?? el.parentElement?.innerText ?? "";
    });
    const price =
      parseMoney(rowText.match(/一口价[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "") ??
      parseMoney(
        rowText.match(/(?:结标|成交(?:价)?)[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "",
      ) ??
      parseMoney(rowText.match(/当前价[\s\S]{0,20}?([¥￥$][\s\d,.]+)/i)?.[1] ?? "");
    if (price == null) continue;

    const tradeType: ListItem["tradeType"] = /一口价/.test(rowText)
      ? "FLOOR"
      : "AUCTION";

    items.push(buildItem(title, price, tradeType, rowText));
  }

  return dedupeItems(items);
}

function pushItem(
  items: ListItem[],
  rawTitle: string,
  rawPrice: string,
  tradeType: ListItem["tradeType"],
  contextText: string,
  asset: StandardAsset,
  channel: AssetChannel,
) {
  const title = rawTitle.trim();
  const price = parseMoney(rawPrice);
  if (price == null || !matchesAsset(title, asset, channel.searchKeyword)) {
    return;
  }
  items.push(buildItem(title, price, tradeType, `${title}\n${contextText}`));
}

function buildItem(
  title: string,
  price: number,
  tradeType: ListItem["tradeType"],
  rowText: string,
): ListItem {
  const cardCondition = parseCardCondition(title);
  const sentiment = parseSentimentFromText(rowText);
  const capturedAt = parseCapturedDateFromText(rowText) ?? undefined;

  return {
    title,
    price,
    tradeType,
    cardCondition,
    ...sentiment,
    capturedAt,
    info: `[KATAO] ${title.slice(0, 80)}`,
  };
}

function dedupeItems(items: ListItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.tradeType}:${item.price}:${item.cardCondition}:${item.title.slice(0, 40)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
