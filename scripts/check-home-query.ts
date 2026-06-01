import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve("apps/web/.env.local") });
config({ path: resolve(".env") });

import { prisma } from "@everyasset/db";

async function main() {
  const assets = await prisma.standardAsset.findMany({
    where: { isMonitoring: true },
    include: { prices: true, channels: true, holding: true },
  });
  console.log("assets:", assets.length);
  for (const a of assets) {
    console.log(`- ${a.assetKey} | ${a.name} | prices=${a.prices.length} channels=${a.channels.length}`);
  }
  await prisma.$disconnect();
}

main().catch((e) => {
  console.error("DB FAIL:", e);
  process.exit(1);
});
