import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

config({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../../../.env") });

const scraperRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export const scraperConfig = {
  headless: process.env.SCRAPER_HEADLESS !== "false",
  concurrency: Number(process.env.SCRAPER_CONCURRENCY ?? 1),
  requestDelayMs: Number(process.env.SCRAPER_REQUEST_DELAY_MS ?? 3000),
  /** true = 直接用本机 Chrome/Edge，跳过 playwright install */
  useSystemChrome: process.env.SCRAPER_USE_SYSTEM_CHROME === "true",
  checkpointPath: resolve(scraperRoot, "checkpoint.json"),
  /** 环境变量临时指定从某 assetKey 开始（含），优先级高于 checkpoint 文件 */
  startFromAssetKey: process.env.SCRAPER_START_FROM_ASSET_KEY?.trim() || undefined,
} as const;
