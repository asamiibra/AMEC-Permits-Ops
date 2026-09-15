import fs from "node:fs";
import path from "node:path";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const deliveryRoutes = [
  "/engineering", "/engineering/drawing-review", "/permits", "/construction",
  "/completion", "/handover", "/issues", "/notifications", "/owner-decisions",
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
});

test("canonical shell exposes work-oriented navigation without historical taxonomy", async ({ page }) => {
  await page.goto("/home", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Home", exact: true }).last()).toBeVisible();
  const labels = await page.locator("nav[aria-label='Primary navigation'] .nav-item").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("aria-label")));
  expect(labels).toEqual(["Home", "AMEC Work", "Opportunities & Proposals", "Contract & Mobilization", "Projects & Delivery", "Billing & Finance", "Content Library"]);
  expect(labels.join(" ")).not.toMatch(/week|phase|source\s*\d+/i);
  const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((violation) => ["critical", "serious"].includes(violation.impact || ""));
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  const evidenceDir = path.resolve(process.cwd(), "../artifacts/ui-product-surface-closure/browser");
  fs.mkdirSync(evidenceDir, { recursive: true });
  await page.screenshot({ path: path.join(evidenceDir, "home-1440.png"), fullPage: true });
});

test("delivery and cross-cutting deep links remain in the product shell", async ({ page }) => {
  const visited: string[] = [];
  for (const route of deliveryRoutes) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("main").first()).toBeVisible();
    expect(new URL(page.url()).pathname, route).toBe(route);
    visited.push(new URL(page.url()).pathname);
  }
  const evidenceDir = path.resolve(process.cwd(), "../artifacts/ui-product-surface-closure/browser");
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, "deep-links.json"), JSON.stringify({ routes: visited, api_mode: "synthetic_mocked_no_writes" }, null, 2));
});
