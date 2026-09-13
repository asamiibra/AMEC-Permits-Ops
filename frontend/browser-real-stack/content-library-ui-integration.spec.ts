import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Content Library first-class UI integration", () => {
  test("canonical route, four libraries, aliases, and specialized route boundary", async ({ page }) => {
    await page.goto("/content-library");
    await expect(page).toHaveURL(/\/content-library$/);
    await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
    for (const heading of ["Forms", "Reports", "Engineering Works", "Definitions"]) {
      await expect(page.getByRole("heading", { name: heading, level: 3 })).toBeVisible();
    }
    for (const alias of ["/dashboard", "/dashboard-v2", "/library", "/master-content"]) {
      await page.goto(alias);
      await expect(page).toHaveURL(/\/content-library$/);
    }
    await page.goto("/dashboard/inputs-go-live");
    await expect(page).toHaveURL(/\/dashboard\/inputs-go-live$/);
  });

  test("library deep links and persona-scoped navigation remain usable on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/content-library/reports");
    await expect(page.getByRole("heading", { name: "Reports", level: 3 })).toBeVisible();
    await expect(page.getByRole("link", { name: /Reports/ })).toHaveAttribute("aria-current", "page");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("navigation", { name: "Mobile primary navigation" })).toContainText("Content Library");
    await page.getByRole("button", { name: "Close navigation" }).click();

    for (const role of ["COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"] as const) {
      await page.getByLabel("Persona").selectOption(role);
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("navigation", { name: "Mobile primary navigation" }).getByRole("button", { name: "Content Library" })).toBeVisible();
      await expect(page.getByLabel("Persona")).toHaveValue(role);
      await page.getByRole("button", { name: "Close navigation" }).click();
    }

    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter((item) => ["serious", "critical"].includes(item.impact || ""))).toEqual([]);
  });
});
