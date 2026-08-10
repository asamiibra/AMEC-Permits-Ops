import { test, expect } from "@playwright/test";

test("Operating Guide opens from the AMEC Work shell", async ({ page }) => {
  await page.goto("/work");
  await page.getByRole("button", { name: "Operating Guide" }).first().click();
  await expect(page).toHaveURL(/\/operating-guide$/);
  await expect(page.getByRole("heading", { name: /ProposalOps helps AMEC move work from tender/ })).toBeVisible();
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(7);
});

test("Arabic Guide is RTL and isolates mixed identifiers", async ({ page }) => {
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator(".about-page")).toHaveAttribute("lang", "ar-EG");
  await expect(page.locator(".about-page")).toHaveAttribute("dir", "rtl");
  expect(await page.locator('bdi[dir="ltr"]').count()).toBeGreaterThan(15);
  await expect(page.getByRole("heading", { name: "دورة عمل AMEC" })).toBeVisible();
});

test("Arabic mobile keeps the seven-stage lifecycle without overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(7);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
});
