import { test, expect } from "@playwright/test";

test("About route exposes the business explainer from the normal app shell", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
  await page.getByRole("button", { name: "Explore PermitOps" }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.getByRole("heading", { name: /PermitOps helps AMEC/ })).toBeVisible();
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(8);
  await expect(page.getByText("final submission", { exact: false }).first()).toBeVisible();
});

test("Arabic mode is RTL and isolates technical terms", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator(".about-page")).toHaveAttribute("lang", "ar-EG");
  await expect(page.locator(".about-page")).toHaveAttribute("dir", "rtl");
  await expect(page.locator('bdi[dir="ltr"]')).toHaveCount(153);
  await expect(page.getByRole("heading", { name: "PermitOps بيشتغل إزاي؟" })).toBeVisible();
});

test("Arabic mobile keeps the lifecycle chronological without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator(".about-lifecycle")).toHaveCSS("display", "flex");
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(8);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
});
