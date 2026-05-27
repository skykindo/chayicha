import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("apps/web/.env.local") });

import { prisma } from "@everyasset/db";

async function main() {
  const targets = await prisma.targetItem.findMany({
    where: { isMonitoring: true },
    include: {
      prices: { orderBy: { capturedAt: "asc" }, take: 90 },
    },
    orderBy: { updatedAt: "desc" },
  });

  console.log(
    JSON.stringify(
      targets.map((t) => ({
        name: t.name,
        priceCount: t.prices.length,
        prices: t.prices.map((p) => ({
          capturedAt: p.capturedAt,
          min: p.minFloorPrice,
        })),
      })),
      null,
      2,
    ),
  );

  await prisma.$disconnect();
}

main().catch(console.error);
