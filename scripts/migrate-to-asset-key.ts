/**
 * 一次性迁移：assetId (UUID) → assetKey (业务主键)
 *
 * 用法: npx tsx scripts/migrate-to-asset-key.ts
 */
import { config } from "dotenv";
import { resolve } from "path";
import { PrismaClient } from "@prisma/client";

config({ path: resolve(".env") });

const prisma = new PrismaClient();

function buildDefaultKey(row: {
  category: string;
  language: string | null;
  series: string | null;
  cardNumber: string | null;
  rarity: string | null;
  name: string;
}): string {
  const parts = [
    row.category,
    row.language ?? "",
    row.series ?? "",
    row.cardNumber ?? "",
    row.rarity ?? "",
  ].filter(Boolean);
  if (parts.length >= 3) return parts.join("-");
  return `Legacy-${row.name.replace(/\s+/g, "-")}`;
}

async function columnExists(table: string, column: string): Promise<boolean> {
  const rows = await prisma.$queryRaw<Array<{ exists: boolean }>>`
    SELECT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = ${table}
        AND column_name = ${column}
    ) AS exists
  `;
  return rows[0]?.exists ?? false;
}

async function main() {
  const hasAssetKey = await columnExists("StandardAsset", "assetKey");
  const hasAssetId = await columnExists("StandardAsset", "assetId");

  if (hasAssetKey && !hasAssetId) {
    console.log("[migrate] 已是 assetKey 结构，跳过");
    return;
  }

  if (!hasAssetKey) {
    console.log("[migrate] StandardAsset 添加 assetKey …");
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "StandardAsset" ADD COLUMN IF NOT EXISTS "assetKey" TEXT`,
    );

    const assets = await prisma.$queryRaw<
      Array<{
        id: string;
        name: string;
        category: string;
        language: string | null;
        series: string | null;
        cardNumber: string | null;
        rarity: string | null;
      }>
    >`SELECT id, name, category, language::text, series, "cardNumber", rarity FROM "StandardAsset"`;

    for (const asset of assets) {
      const assetKey = buildDefaultKey(asset);
      await prisma.$executeRaw`
        UPDATE "StandardAsset" SET "assetKey" = ${assetKey} WHERE id = ${asset.id}::uuid
      `;
      console.log(`  ${asset.name} → ${assetKey}`);
    }

    await prisma.$executeRawUnsafe(
      `ALTER TABLE "StandardAsset" ALTER COLUMN "assetKey" SET NOT NULL`,
    );
    await prisma.$executeRawUnsafe(
      `CREATE UNIQUE INDEX IF NOT EXISTS "StandardAsset_assetKey_key" ON "StandardAsset"("assetKey")`,
    );
  }

  async function migrateChild(
    table: "AssetChannel" | "PriceStream" | "Holding",
  ) {
    const childHasKey = await columnExists(table, "assetKey");
    const childHasId = await columnExists(table, "assetId");

    if (childHasKey && !childHasId) {
      console.log(`[migrate] ${table} 已迁移，跳过`);
      return;
    }

    console.log(`[migrate] ${table} …`);
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "${table}" ADD COLUMN IF NOT EXISTS "assetKey" TEXT`,
    );
    await prisma.$executeRawUnsafe(`
      UPDATE "${table}" c
      SET "assetKey" = a."assetKey"
      FROM "StandardAsset" a
      WHERE c."assetId" = a.id AND c."assetKey" IS NULL
    `);
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "${table}" DROP CONSTRAINT IF EXISTS "${table}_assetId_fkey"`,
    );
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "${table}" ALTER COLUMN "assetKey" SET NOT NULL`,
    );
    await prisma.$executeRawUnsafe(
      `ALTER TABLE "${table}" DROP COLUMN IF EXISTS "assetId"`,
    );
    await prisma.$executeRawUnsafe(`
      ALTER TABLE "${table}"
      ADD CONSTRAINT "${table}_assetKey_fkey"
      FOREIGN KEY ("assetKey") REFERENCES "StandardAsset"("assetKey")
      ON DELETE CASCADE ON UPDATE CASCADE
    `);
  }

  await migrateChild("AssetChannel");
  await migrateChild("PriceStream");

  const holdingExists = await prisma.$queryRaw<Array<{ exists: boolean }>>`
    SELECT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'Holding'
    ) AS exists
  `;
  if (holdingExists[0]?.exists) {
    await migrateChild("Holding");
  }

  console.log("[migrate] 完成，请运行 npm run db:push 对齐 schema");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
