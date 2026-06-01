/**
 * 从 卡牌-import.csv 批量写入 StandardAsset（绕过 Supabase CSV 导入限制）
 *
 * 用法: npx tsx scripts/import-standard-assets.ts
 * 可选: npx tsx scripts/import-standard-assets.ts 卡牌-import.csv
 */
import { config } from "dotenv";
import { readFileSync } from "fs";
import { resolve } from "path";
import { AssetCategory, CardLanguage, prisma } from "@everyasset/db";

config({ path: resolve(".env") });

type Row = {
  assetKey: string;
  name: string;
  category: AssetCategory;
  isMonitoring: boolean;
  series: string | null;
  cardNumber: string | null;
  language: CardLanguage | null;
  rarity: string | null;
  year: number | null;
  imageUrl: string | null;
};

function parseCsv(text: string): Row[] {
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const header = lines[0].split(",");
  const idx = (name: string) => {
    const i = header.indexOf(name);
    if (i < 0) throw new Error(`CSV 缺少列: ${name}`);
    return i;
  };
  const col = {
    assetKey: idx("assetKey"),
    name: idx("name"),
    category: idx("category"),
    isMonitoring: idx("isMonitoring"),
    series: idx("series"),
    cardNumber: idx("cardNumber"),
    language: idx("language"),
    rarity: idx("rarity"),
    year: idx("year"),
    imageUrl: idx("imageUrl"),
  };

  const rows: Row[] = [];
  for (let n = 1; n < lines.length; n++) {
    const line = lines[n];
    if (!line.trim()) continue;
    const parts = line.split(",");
    const get = (i: number) => (parts[i]?.trim() ? parts[i].trim() : null);

    const assetKey = get(col.assetKey);
    const name = get(col.name);
    if (!assetKey || !name) continue;

    const lang = get(col.language);
    const yearRaw = get(col.year);

    rows.push({
      assetKey,
      name,
      category: get(col.category) as AssetCategory,
      isMonitoring: get(col.isMonitoring) !== "false",
      series: get(col.series),
      cardNumber: get(col.cardNumber),
      language: lang ? (lang as CardLanguage) : null,
      rarity: get(col.rarity),
      year: yearRaw ? Number(yearRaw) : null,
      imageUrl: get(col.imageUrl),
    });
  }
  return rows;
}

async function main() {
  const file = process.argv[2] ?? "卡牌-import.csv";
  const path = resolve(file);
  const rows = parseCsv(readFileSync(path, "utf8"));
  console.log(`[import] 读取 ${rows.length} 行，开始 upsert …`);

  let ok = 0;
  let failed = 0;

  for (const row of rows) {
    try {
      await prisma.standardAsset.upsert({
        where: { assetKey: row.assetKey },
        create: row,
        update: {
          name: row.name,
          category: row.category,
          isMonitoring: row.isMonitoring,
          series: row.series,
          cardNumber: row.cardNumber,
          language: row.language,
          rarity: row.rarity,
          year: row.year,
          imageUrl: row.imageUrl,
        },
      });
      ok += 1;
    } catch (e) {
      failed += 1;
      console.error(`[import] ✗ ${row.assetKey}:`, e instanceof Error ? e.message : e);
    }
  }

  console.log(`[import] 完成: 成功 ${ok} / 失败 ${failed}`);
  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
