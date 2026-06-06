import { prisma, parseCardCondition, type Platform } from "@everyasset/db";
import { toCapturedDateString } from "./utils/parse-sentiment.js";

export type StreamInput = {
  assetKey: string;
  platform: Platform;
  tradeType: "AUCTION" | "FLOOR";
  cardCondition?: string | null;
  price: number;
  info?: string | null;
  bidCount?: number | null;
  bidderCount?: number | null;
  watchCount?: number | null;
  isDelayed?: boolean;
  capturedAt?: Date;
};

export async function upsertPriceStream(input: StreamInput) {
  const capturedAt = input.capturedAt ?? new Date();
  const capturedDate = toCapturedDateString(capturedAt);
  const info = input.info?.trim() || "";
  const cardCondition =
    input.cardCondition ?? parseCardCondition(info, null);

  return prisma.priceStream.upsert({
    where: {
      assetKey_platform_tradeType_price_capturedDate_cardCondition_info_dealSeq: {
        assetKey: input.assetKey,
        platform: input.platform,
        tradeType: input.tradeType,
        price: input.price,
        capturedDate,
        cardCondition,
        info,
        dealSeq: 0,
      },
    },
    create: {
      assetKey: input.assetKey,
      platform: input.platform,
      tradeType: input.tradeType,
      cardCondition,
      price: input.price,
      info: info || null,
      bidCount: input.bidCount ?? null,
      bidderCount: input.bidderCount ?? null,
      watchCount: input.watchCount ?? null,
      isDelayed: input.isDelayed ?? false,
      capturedAt,
      capturedDate,
      dealSeq: 0,
    },
    update: {
      bidCount: input.bidCount ?? null,
      bidderCount: input.bidderCount ?? null,
      watchCount: input.watchCount ?? null,
      isDelayed: input.isDelayed ?? false,
      capturedAt,
    },
  });
}
