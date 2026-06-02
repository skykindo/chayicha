/**
 * 从 vision-channels.csv 同步 VISION 渠道（本地改 CSV → 一条命令入库）
 *
 * 用法:
 *   npx tsx scripts/import-vision-channels.ts
 *   npx tsx scripts/import-vision-channels.ts vision-channels.csv
 *   npx tsx scripts/import-vision-channels.ts --sync   # 删除 CSV 中已移除的渠道
 *   npx tsx scripts/import-vision-channels.ts --dry-run
 */
import { config } from "dotenv";
import { readFileSync } from "fs";
import { resolve } from "path";
import { Platform, TrackType, prisma } from "@everyasset/db";

config({ path: resolve(".env") });

type Row = {
  assetKey: string;
  trackType: TrackType;
  platform: Platform;
  sourceUrl: string | null;
  sourceUrlAuction: string | null;
  searchKeyword: string | null;
};

const COLS = [
  "assetKey",
  "trackType",
  "platform",
  "sourceUrl",
  "sourceUrlAuction",
  "searchKeyword",
] as const;

function parseCsv(text: string): Row[] {
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (!lines.length) return [];

  const header = lines[0].split(",").map((c) => c.trim());
  const idx = (name: string) => {
    const i = header.indexOf(name);
    if (i < 0) throw new Error(`CSV 缺少列: ${name}`);
    return i;
  };
  const col = Object.fromEntries(COLS.map((c) => [c, idx(c)])) as Record<
    (typeof COLS)[number],
    number
  >;

  const rows: Row[] = [];
  for (let n = 1; n < lines.length; n++) {
    const line = lines[n];
    if (!line.trim()) continue;
    const parts = line.split(",");
    const get = (i: number) => {
      const v = parts[i]?.trim();
      return v ? v : null;
    };

    const assetKey = get(col.assetKey);
    if (!assetKey || assetKey.startsWith("#")) continue;

    rows.push({
      assetKey,
      trackType: (get(col.trackType) ?? "VISION") as TrackType,
      platform: (get(col.platform) ?? "JIHUANSHE") as Platform,
      sourceUrl: get(col.sourceUrl),
      sourceUrlAuction: get(col.sourceUrlAuction),
      searchKeyword: get(col.searchKeyword),
    });
  }
  return rows;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const sync = args.includes("--sync");
  const dryRun = args.includes("--dry-run");
  const file = args.find((a) => !a.startsWith("--")) ?? "vision-channels.csv";
  return { sync, dryRun, file: resolve(file) };
}

async function main() {
  const { sync, dryRun, file } = parseArgs();
  const rows = parseCsv(readFileSync(file, "utf8"));
  console.log(`[vision-import] 读取 ${rows.length} 行 ← ${file}`);

  const seen = new Set<string>();
  let ok = 0;
  let failed = 0;

  for (const row of rows) {
    const key = `${row.assetKey}::${row.platform}`;
    if (seen.has(key)) {
      console.warn(`[vision-import] 跳过重复行: ${row.assetKey} / ${row.platform}`);
      continue;
    }
    seen.add(key);

    const asset = await prisma.standardAsset.findUnique({
      where: { assetKey: row.assetKey },
      select: { assetKey: true, name: true },
    });
    if (!asset) {
      failed += 1;
      console.error(`[vision-import] ✗ ${row.assetKey}: StandardAsset 不存在`);
      continue;
    }

    if (dryRun) {
      console.log(`[vision-import] (dry) ${row.assetKey} → ${row.platform} ${row.trackType}`);
      ok += 1;
      continue;
    }

    try {
      await prisma.assetChannel.upsert({
        where: {
          assetKey_platform: {
            assetKey: row.assetKey,
            platform: row.platform,
          },
        },
        create: row,
        update: {
          trackType: row.trackType,
          sourceUrl: row.sourceUrl,
          sourceUrlAuction: row.sourceUrlAuction,
          searchKeyword: row.searchKeyword,
        },
      });
      ok += 1;
    } catch (e) {
      failed += 1;
      console.error(
        `[vision-import] ✗ ${row.assetKey}:`,
        e instanceof Error ? e.message : e,
      );
    }
  }

  if (sync && !dryRun) {
    const dbChannels = await prisma.assetChannel.findMany({
      where: { trackType: "VISION", platform: "JIHUANSHE" },
      select: { id: true, assetKey: true, platform: true },
    });
    let removed = 0;
    for (const ch of dbChannels) {
      const key = `${ch.assetKey}::${ch.platform}`;
      if (!seen.has(key)) {
        await prisma.assetChannel.delete({ where: { id: ch.id } });
        console.log(`[vision-import] 已删除（CSV 中无）: ${ch.assetKey}`);
        removed += 1;
      }
    }
    console.log(`[vision-import] --sync 删除 ${removed} 条`);
  }

  console.log(`[vision-import] 完成: 成功 ${ok} / 失败 ${failed}`);
  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
