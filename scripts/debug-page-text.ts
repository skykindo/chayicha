import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { launchBrowser, createOptimizedPage } from "../apps/scraper/src/browser.js";

config({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../.env") });

async function main() {
  const url = process.argv[2] ?? "https://www.cardhobby.com.cn/market/item/111065722";
  const browser = await launchBrowser();
  const ctx = await browser.newContext({ locale: "zh-CN" });
  const page = await createOptimizedPage(ctx);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2000);
  const text = await page.locator("body").innerText();
  for (const key of ["当前价", "一口价", "售价", "起拍", "¥", "价格"]) {
    const idx = text.indexOf(key);
    if (idx >= 0) console.log(`--- ${key} ---\n`, text.slice(idx, idx + 80));
  }
  console.log("--- tail ---\n", text.slice(-500));
  await browser.close();
}

main().catch(console.error);
