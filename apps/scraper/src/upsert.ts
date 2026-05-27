import { prisma, type Platform } from "@everyasset/db";
import { startOfDay } from "./utils/dates.js";

export type StreamInput = {
  assetId: string;
  platform: Platform;
  tradeType: "AUCTION" | "FLOOR";
  gradeLabel?: string | null;
  price: number;
  info?: string | null;
  capturedAt?: Date;
};

export async function upsertPriceStream(input: StreamInput) {
  const capturedAt = startOfDay(input.capturedAt);

  return prisma.priceStream.upsert({
    where: {
      assetId_capturedAt_platform_tradeType: {
        assetId: input.assetId,
        capturedAt,
        platform: input.platform,
        tradeType: input.tradeType,
      },
    },
    create: {
      assetId: input.assetId,
      platform: input.platform,
      tradeType: input.tradeType,
      gradeLabel: input.gradeLabel ?? null,
      price: input.price,
      info: input.info ?? null,
      capturedAt,
    },
    update: {
      price: input.price,
      gradeLabel: input.gradeLabel ?? null,
      info: input.info ?? null,
    },
  });
}
