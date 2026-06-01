import type { Page } from "playwright";
import {
  parseCardCondition,
  parseGradeLabelFromTitle,
  type StandardAsset,
  type AssetChannel,
} from "@everyasset/db";
import { matchesAsset } from "../../utils/match-asset.js";
import { scrollAndLoadMore } from "../../utils/load-more.js";
import {
  parseCapturedDateFromText,
  parseSentimentFromText,
} from "../../utils/parse-sentiment.js";
import { parseMoney } from "../../utils/parse-price.js";
import type { ListItem } from "../types.js";
import {
  extractPokecolorTurnoverCardId,
  scrapePokecolorTurnoverApi,
} from "./api-scraper.js";

/**
 * 卡乐 Pokecolor — 直售与拍卖常为不同列表页：
 * - sourceUrl        → 直售（FLOOR），如 turnover 页
 * - sourceUrlAuction → 拍卖（AUCTION），如 h5 首页竞价区
 */
export async function scrapePokecolorList(
  page: Page,
  channel: AssetChannel,
  asset: StandardAsset,
): Promise<ListItem[]> {
  const jobs: Array<{ url: string; tradeType: ListItem["tradeType"] }> = [];

  if (channel.sourceUrl) {
    jobs.push({ url: channel.sourceUrl, tradeType: "FLOOR" });
  }
  if (channel.sourceUrlAuction) {
    jobs.push({ url: channel.sourceUrlAuction, tradeType: "AUCTION" });
  }
  if (jobs.length === 0) return [];

  const all: ListItem[] = [];

  // 卡乐 turnover 页：走公开 API（无需 H5 登录）
  if (channel.sourceUrl) {
    const cardId = extractPokecolorTurnoverCardId(channel.sourceUrl);
    if (cardId) {
      all.push(...(await scrapePokecolorTurnoverApi(cardId, channel, asset)));
    }
  }

  for (const job of jobs) {
    if (extractPokecolorTurnoverCardId(job.url)) continue;
    all.push(
      ...(await scrapePokecolorPage(
        page,
        job.url,
        channel,
        asset,
        job.tradeType,
      )),
    );
  }

  return dedupeItems(all);
}

async function scrapePokecolorPage(
  page: Page,
  url: string,
  channel: AssetChannel,
  asset: StandardAsset,
  forceTradeType: ListItem["tradeType"],
): Promise<ListItem[]> {
  const isH5 = url.includes("/h5/");

  if (isH5) {
    await page.setViewportSize({ width: 390, height: 844 });
  }

  await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForTimeout(isH5 ? 3500 : 2500);

  // 卡乐 H5 / SPA：先滚动并尝试点「加载更多」
  await scrollAndLoadMore(page, {
    maxScrolls: isH5 ? 8 : 5,
    maxLoadMoreClicks: isH5 ? 5 : 3,
  });

  const bodyText = await page.locator("body").innerText();
  const items: ListItem[] = [];

  if (forceTradeType === "AUCTION") {
    collectByPattern(
      items,
      bodyText,
      /([^\n]{8,160})\n(?:Current Bid|当前出价|拍卖(?:价)?|最高出价|竞价)\n\s*([$¥￥]\s*[\d,]+(?:\.\d+)?)/gi,
      "AUCTION",
      asset,
      channel,
    );
  }

  if (forceTradeType === "FLOOR") {
    collectByPattern(
      items,
      bodyText,
      /([^\n]{8,160})\n(?:Listed Price|Listing Price)\n\s*([$¥￥]\s*[\d,]+(?:\.\d+)?)/gi,
      "FLOOR",
      asset,
      channel,
    );
    collectByPattern(
      items,
      bodyText,
      /([^\n]{8,160})\n(?:挂售价格|售价格|直售价格|成交价)\n\s*([$¥￥]\s*[\d,]+(?:\.\d+)?)/gi,
      "FLOOR",
      asset,
      channel,
    );
  }

  // H5 单行块：标题 ￥1234 / $123.45
  collectByPattern(
    items,
    bodyText,
    /([^\n¥￥$]{6,120})\s+([¥￥$]\s*[\d,]+(?:\.\d+)?)/g,
    forceTradeType,
    asset,
    channel,
  );

  const links = await page.locator('a[href*="/products/"]').all();
  for (const link of links.slice(0, 80)) {
    const href = await link.getAttribute("href");
    const title = (await link.innerText()).trim();
    if (!title || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    if (href) void href;
  }

  return items;
}

function collectByPattern(
  items: ListItem[],
  bodyText: string,
  pattern: RegExp,
  tradeType: ListItem["tradeType"],
  asset: StandardAsset,
  channel: AssetChannel,
) {
  for (const match of bodyText.matchAll(pattern)) {
    const title = match[1].trim();
    const price = parseMoney(match[2]);
    if (price == null || !matchesAsset(title, asset, channel.searchKeyword)) {
      continue;
    }
    items.push({
      title,
      price,
      tradeType,
      cardCondition: parseCardCondition(title, parseGradeLabelFromTitle(title)),
      gradeLabel: parseGradeLabelFromTitle(title) ?? "裸卡",
      ...parseSentimentFromText(`${title}\n${bodyText}`),
      capturedAt: parseCapturedDateFromText(`${title}\n${bodyText}`) ?? undefined,
      info: `[POKECOLOR/${tradeType}] ${title.slice(0, 80)}`,
    });
  }
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
