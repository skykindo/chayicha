import type { StandardAsset, AssetChannel } from "@everyasset/db";
import {
  buildGradeLabel,
  parseCardCondition,
} from "@everyasset/db";
import { matchesAsset } from "../../utils/match-asset.js";
import type { ListItem } from "../types.js";

type SellOrderRow = {
  display_title: string;
  price: string;
  sell_mode_category?: string;
  rate_type?: string | null;
  rate_score?: string | null;
  rate_score_display?: string | null;
  display_status?: string;
  order_deal_on?: string | null;
  bid_count?: number | null;
  bidder_count?: number | null;
  watch_count?: number | null;
};

type SellOrderResponse = {
  code: number;
  data?: {
    count: number;
    next: boolean;
    results: SellOrderRow[];
  };
};

const TURNOVER_CARD_ID_RE =
  /pages-collection\/turnover\/index\?id=(\d+)/i;

export function extractPokecolorTurnoverCardId(url: string): string | null {
  return url.match(TURNOVER_CARD_ID_RE)?.[1] ?? null;
}

/**
 * 卡乐 turnover 公开 JSON API — 全量成交记录入库
 */
export async function scrapePokecolorTurnoverApi(
  cardId: string,
  channel: AssetChannel,
  asset: StandardAsset,
): Promise<ListItem[]> {
  const items: ListItem[] = [];
  let page = 1;
  let hasNext = true;

  while (hasNext && page <= 10) {
    const url = new URL(
      `https://api.pokecolor.cn/api/h5/card/deal/card/${cardId}/sellorder/`,
    );
    url.searchParams.set("page", String(page));
    url.searchParams.set("page_size", "50");
    url.searchParams.set("order_by", "-order_deal_on");

    const res = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) break;

    const json = (await res.json()) as SellOrderResponse;
    if (json.code !== 100 || !json.data?.results?.length) break;

    for (const row of json.data.results) {
      const title = row.display_title?.trim();
      const price = parseFloat(row.price);
      if (!title || Number.isNaN(price)) continue;

      if (!matchesAsset(title, asset, channel.searchKeyword)) continue;

      const gradeLabel = buildGradeLabel(
        row.rate_type,
        row.rate_score_display,
        row.rate_score,
      );

      const cardCondition = parseCardCondition(title, gradeLabel);

      const tradeType: ListItem["tradeType"] =
        row.sell_mode_category === "bid" ||
        /拍卖|bid/i.test(row.display_status ?? "")
          ? "AUCTION"
          : "FLOOR";

      const capturedAt = row.order_deal_on
        ? new Date(row.order_deal_on)
        : undefined;

      items.push({
        title,
        price,
        tradeType,
        cardCondition,
        gradeLabel,
        bidCount: row.bid_count ?? null,
        bidderCount: row.bidder_count ?? null,
        watchCount: row.watch_count ?? null,
        isDelayed: false,
        capturedAt,
        info: `[POKECOLOR/API] ${gradeLabel} ${title.slice(0, 60)}`,
      });
    }

    hasNext = json.data.next;
    page += 1;
  }

  return dedupeItems(items);
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
