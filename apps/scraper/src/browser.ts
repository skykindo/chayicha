import { existsSync } from "fs";
import { chromium, type Browser } from "playwright";
import { scraperConfig } from "./config.js";

const SYSTEM_BROWSER_PATHS = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
] as const;

/** 优先用本机 Chrome / Edge（省 180MB 下载）；失败再试 Playwright 自带 Chromium */
export async function launchBrowser(): Promise<Browser> {
  if (scraperConfig.useSystemChrome) {
    for (const executablePath of SYSTEM_BROWSER_PATHS) {
      if (!existsSync(executablePath)) continue;
      console.log(`[browser] 使用本机浏览器: ${executablePath}`);
      return chromium.launch({
        headless: scraperConfig.headless,
        executablePath,
      });
    }
  }

  try {
    return await chromium.launch({ headless: scraperConfig.headless });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    if (msg.includes("Executable doesn't exist") || msg.includes("ENOSPC")) {
      throw new Error(
        "无法启动浏览器：C 盘空间不足（需至少 500MB 空闲）或未安装 Chrome/Edge。请清理 C 盘后再试。",
      );
    }
    throw error;
  }
}

export async function createBrowserContext() {
  const browser = await launchBrowser();

  return browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    viewport: { width: 1280, height: 720 },
    locale: "zh-CN",
  });
}

export async function createOptimizedPage(
  context: Awaited<ReturnType<typeof createBrowserContext>>,
) {
  const page = await context.newPage();

  await page.route("**/*", (route) => {
    const type = route.request().resourceType();
    if (["image", "media", "font"].includes(type)) {
      route.abort();
      return;
    }
    route.continue();
  });

  return page;
}
