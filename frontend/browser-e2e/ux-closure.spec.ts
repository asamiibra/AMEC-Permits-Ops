import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const navLabels = ["Home", "Content Library", "Proposals", "Contracts", "Billing"];

test.describe("four-module UX closure", () => {
  test("Home communicates the foundation and commercial workflow", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/home", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Keep work moving from source to cash." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Content Library" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "From Proposal to Billing" })).toBeVisible();
    await expect(page.locator("[data-testid='home-module-card']")).toHaveCount(3);
    await expect(page.locator("nav[aria-label='Primary navigation']")).toContainText("WORKFLOW");

    const labels = await page.locator("nav[aria-label='Primary navigation'] .nav-item").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("aria-label")));
    expect(labels).toEqual(navLabels);
    await expect(page.locator("body")).not.toContainText(/Opportunity \/ Proposal \/ Client Tender|Contract \/ Mobilization|Billing \/ Invoice \/ Receivables \/ Collection/);
    await expect(page.locator("body")).not.toContainText(/[⌂↗▤¤▦]/u);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);

    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter((item) => ["critical", "serious"].includes(item.impact || ""))).toEqual([]);
  });

  test("mobile navigation preserves order and exposes an operable drawer", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/home", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Open navigation" }).click();
    const drawer = page.getByRole("navigation", { name: "Mobile primary navigation" });
    await expect(drawer).toBeVisible();
    const labels = await drawer.locator(".nav-item").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("aria-label")));
    expect(labels).toEqual(navLabels);
    await expect(drawer).toContainText("WORKFLOW");
    await page.getByRole("button", { name: "Close navigation" }).click();
    await expect(drawer).toBeHidden();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  });
});
