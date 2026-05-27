import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

config({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../../../.env") });

export const scraperConfig = {
  headless: process.env.SCRAPER_HEADLESS !== "false",
  concurrency: Number(process.env.SCRAPER_CONCURRENCY ?? 1),
  requestDelayMs: Number(process.env.SCRAPER_REQUEST_DELAY_MS ?? 3000),
  /** true = 直接用本机 Chrome/Edge，跳过 playwright install */
  useSystemChrome: process.env.SCRAPER_USE_SYSTEM_CHROME === "true",
} as const;
