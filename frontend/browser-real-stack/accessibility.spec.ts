import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const routes = ["/work", "/permits", "/opportunities", "/engineering-closeout", "/reviews", "/issues", "/notifications", "/about", "/admin", "/admin/go-live-readiness"];

test("core owner routes have no critical or serious axe violations in English and Arabic", async ({ page }) => {
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const english = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(english.violations.filter((item) => ["critical", "serious"].includes(item.impact || "")), route).toEqual([]);
    await page.locator(".global-language-switch").click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    const arabic = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(arabic.violations.filter((item) => ["critical", "serious"].includes(item.impact || "")), `${route} Arabic`).toEqual([]);
    await page.locator(".global-language-switch").click();
  }
});

test("keyboard reaches the primary owner controls", async ({ page }) => {
  await page.goto("/permits");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  await expect(page.getByRole("button", { name: /Permits/ }).first()).toBeVisible();
});
