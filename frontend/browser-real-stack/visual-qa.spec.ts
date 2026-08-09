import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const routes = [
  "work", "permits", "opportunities", "engineering-closeout", "reviews", "issues", "notifications", "about",
  "how-permitops-works", "admin", "admin/go-live-readiness", "admin/documents", "admin/conflicts", "admin/lineage",
  "admin/attachments-grids", "admin/control-diagnostics", "admin/expansion-foundation", "admin/municipality",
];
const output = path.resolve(process.cwd(), "../artifacts/pre-client-final-closure/screenshots");

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("permitops-role")) sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN");
    if (!localStorage.getItem("permitops-locale")) localStorage.setItem("permitops-locale", "en");
  });
});

test("captures the owner/client visual QA set in both locales", async ({ page }) => {
  fs.mkdirSync(output, { recursive: true });
  const manifest: Array<Record<string, unknown>> = [];
  for (const route of routes) {
    for (const locale of ["en", "ar"] as const) {
      await page.goto(`/${route}`);
      if (locale === "ar") await page.locator(".global-language-switch").click();
      await expect(page.locator("html")).toHaveAttribute("lang", locale === "ar" ? "ar-EG" : "en");
      await page.waitForTimeout(120);
      const file = path.join(output, `${route.replaceAll("/", "-")}-${locale}-desktop.png`);
      await page.screenshot({ path: file, fullPage: true });
      const dimensions = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }));
      manifest.push({ route: `/${route}`, locale, viewport: "desktop", file: path.relative(process.cwd(), file), ...dimensions, horizontal_overflow: dimensions.width > 1442 });
      if (locale === "ar") await page.locator(".global-language-switch").click();
    }
  }
  fs.writeFileSync(path.join(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  expect(manifest).toHaveLength(36);
});
