import { config } from "dotenv";
import { resolve } from "path";

config({ path: resolve(".env") });

import { prisma } from "@everyasset/db";

async function main() {
  const cols = await prisma.$queryRaw<
    Array<{ column_name: string; data_type: string; is_nullable: string }>
  >`
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'StandardAsset'
    ORDER BY ordinal_position
  `;
  console.log(cols.map((c) => `${c.column_name} (${c.data_type}, nullable=${c.is_nullable})`).join("\n"));
  await prisma.$disconnect();
}

main().catch(console.error);
