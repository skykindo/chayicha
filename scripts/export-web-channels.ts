/**
 * 导出 WEB 渠道到 web-channels.csv
 *
 * 用法: npx tsx scripts/export-web-channels.ts
 */
import { config } from "dotenv";
import { writeFileSync } from "fs";
import { resolve } from "path";
import { prisma } from "@everyasset/db";

config({ path: resolve(".env") });

const HEADER =
  "assetKey,trackType,platform,sourceUrl,sourceUrlAuction,searchKeyword";

function csvEscape(value: string | null | undefined): string {
  if (!value) return "";
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

async function main() {
  const file = resolve(process.argv[2] ?? "web-channels.csv");

  const channels = await prisma.assetChannel.findMany({
    where: { trackType: "WEB" },
    orderBy: { createdAt: "asc" },
  });

  const lines = [HEADER];
  for (const ch of channels) {
    lines.push(
      [
        ch.assetKey,
        ch.trackType,
        ch.platform,
        ch.sourceUrl,
        ch.sourceUrlAuction,
        ch.searchKeyword,
      ]
        .map(csvEscape)
        .join(","),
    );
  }

  writeFileSync(file, `${lines.join("\n")}\n`, "utf8");
  console.log(`[web-export] 导出 ${channels.length} 条 → ${file}`);
  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
