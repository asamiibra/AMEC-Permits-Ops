import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("Operating Guide has no critical or serious accessibility violations in English and Arabic", async ({ page }) => {
  await page.goto("/operating-guide");
  const english = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(english.violations.filter((item) => ["critical", "serious"].includes(item.impact || ""))).toEqual([]);
  await page.getByRole("button", { name: "العربي" }).click();
  const arabic = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(arabic.violations.filter((item) => ["critical", "serious"].includes(item.impact || ""))).toEqual([]);
});

test("language control is keyboard reachable and exposes state", async ({ page }) => {
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "English" }).focus();
  await expect(page.locator(":focus")).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toHaveAttribute("aria-pressed", "false");
});
