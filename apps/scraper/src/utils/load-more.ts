import type { Page } from "playwright";

type LoadMoreOptions = {
  maxScrolls?: number;
  maxLoadMoreClicks?: number;
  pauseMs?: number;
};

const LOAD_MORE_SELECTORS = [
  "text=加载更多",
  "text=Load more",
  "text=查看更多",
  "text=点击加载更多",
  "text=上拉加载更多",
  '[class*="load-more"]',
  '[class*="loadMore"]',
];

/**
 * 滚动 + 点击「加载更多」，尽量多拉几屏列表项。
 * 无法保证覆盖全部无限滚动，但比只读首屏更完整。
 */
export async function scrollAndLoadMore(
  page: Page,
  options: LoadMoreOptions = {},
) {
  const maxScrolls = options.maxScrolls ?? 5;
  const maxLoadMoreClicks = options.maxLoadMoreClicks ?? 3;
  const pauseMs = options.pauseMs ?? 900;

  for (let i = 0; i < maxScrolls; i++) {
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });
    await page.waitForTimeout(pauseMs);
  }

  for (let i = 0; i < maxLoadMoreClicks; i++) {
    let clicked = false;
    for (const selector of LOAD_MORE_SELECTORS) {
      const target = page.locator(selector).first();
      const visible = await target.isVisible().catch(() => false);
      if (!visible) continue;

      await target.click({ timeout: 3000 }).catch(() => undefined);
      await page.waitForTimeout(pauseMs + 400);
      clicked = true;
      break;
    }
    if (!clicked) break;

    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });
    await page.waitForTimeout(pauseMs);
  }
}
