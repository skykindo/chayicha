import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve(".env") });

import { prisma } from "@everyasset/db";

async function main() {
  const assets = await prisma.standardAsset.findMany({
    include: {
      channels: true,
      prices: { orderBy: { capturedAt: "desc" }, take: 5 },
    },
  });

  for (const asset of assets) {
    console.log(`\n=== ${asset.name} ===`);
    console.log(`channels: ${asset.channels.length}`);
    for (const ch of asset.channels) {
      console.log(`  - ${ch.platform} ${ch.trackType} ${ch.sourceUrl?.slice(0, 50) ?? ch.searchKeyword}`);
    }
    console.log(`prices: ${asset.prices.length}`);
    for (const p of asset.prices) {
      console.log(
        `  ${p.capturedAt.toISOString().slice(0, 10)} ${p.platform}/${p.tradeType} ¥${p.price}`,
      );
    }
  }

  await prisma.$disconnect();
}

main().catch(console.error);
