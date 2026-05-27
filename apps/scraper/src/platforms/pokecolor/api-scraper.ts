import type { StandardAsset, AssetChannel } from "@everyasset/db";
import { buildGradeLabel, matchesGradeSpec } from "@everyasset/db";
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
 * 卡乐 turnover 页（如 id=239864 超级快龙 ex）走公开 JSON API，
 * 无需 H5 登录。含 rate_type / rate_score_display 结构化评级字段。
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

      if (!matchesGradeSpec(asset, gradeLabel)) continue;

      const tradeType: ListItem["tradeType"] =
        row.sell_mode_category === "bid" ||
        /拍卖|bid/i.test(row.display_status ?? "")
          ? "AUCTION"
          : "FLOOR";

      items.push({
        title,
        price,
        tradeType,
        gradeLabel,
        info: `[POKECOLOR/API] ${gradeLabel} ${title.slice(0, 60)}`,
      });
    }

    hasNext = json.data.next;
    page += 1;
  }

  return pickLatestPerTradeType(items);
}

/** turnover API 为成交记录，同 tradeType 取最近一条（API 已按成交时间倒序） */
function pickLatestPerTradeType(items: ListItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = item.tradeType;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
