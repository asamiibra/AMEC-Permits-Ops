import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");
const evidenceRoot = path.join(repoRoot, "artifacts", "home-command-center");
const expectedOwnerNav = [
  "Home",
  "Intake & Opportunity",
  "Contract & Mobilization",
  "Design & Technical Delivery",
  "Regulatory & Submissions",
  "Construction & Post-Approval",
  "Completion & As-Built",
  "Handover & Closeout",
  "Admin",
  "Operating Guide",
];

test("Home is the command center with seven business stages and preserved canonical entry points", async ({ page }) => {
  fs.mkdirSync(evidenceRoot, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/home", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".home-stage-card").first()).toBeVisible({ timeout: 15000 });
  await expect.poll(() => page.locator(".home-attention-counts strong").first().textContent()).not.toBe("—");

  const nav = await page.locator("nav[aria-label='Primary navigation'] .nav-item").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("aria-label") || ""));
  expect(nav).toEqual(expectedOwnerNav);
  for (const label of ["AMEC Work", "Finance", "Content Library", "Issues", "Notifications"]) {
    await expect(page.locator("nav[aria-label='Primary navigation']")).not.toContainText(label);
  }

  expect(await page.locator(".home-stage-card").count()).toBe(7);
  expect(await page.locator(".home-attention-row").count()).toBe(Number(await page.locator(".home-attention-counts strong").first().textContent()));
  await expect(page.getByRole("link", { name: /Open Finance/ })).toHaveAttribute("href", "/billing");
  await expect(page.getByRole("link", { name: /Open Content Library/ })).toHaveAttribute("href", "/dashboard");
  await expect(page.locator(".home-activity-row")).toHaveCount(3);
  await expect(page.getByRole("button", { name: /Notifications/ })).toBeVisible();

  const stageTargets = await page.locator(".home-stage-card").evaluateAll((nodes) => nodes.map((node) => (node as HTMLAnchorElement).getAttribute("href")));
  expect(stageTargets).toEqual(["/opportunities", "/contract-mobilization", "/engineering", "/permits", "/construction", "/completion", "/handover"]);

  const views = [
    ["All", 0],
    ["Actions", 1],
    ["Reviews", 2],
    ["Exceptions", 3],
    ["Overdue", 4],
  ] as const;
  for (const [label, index] of views) {
    await page.getByRole("button", { name: label, exact: true }).click();
    const count = Number(await page.locator(".home-attention-counts strong").nth(index).textContent());
    expect(await page.locator(".home-attention-row").count(), `${label} count/row parity`).toBe(count);
  }

  await page.screenshot({ path: path.join(evidenceRoot, "home-1440.png"), fullPage: true });
  const axe = await new AxeBuilder({ page }).analyze();
  const seriousOrCritical = axe.violations.filter((item) => item.impact === "serious" || item.impact === "critical");
  expect(seriousOrCritical).toEqual([]);
  fs.writeFileSync(path.join(evidenceRoot, "home-acceptance.json"), JSON.stringify({ nav, stageTargets, countRowParity: true, seriousOrCritical: [] }, null, 2));
});

test("Home remains usable at required responsive widths and legacy routes stay reachable", async ({ page }) => {
  const responsive: Array<[number, number]> = [[1920, 1080], [1440, 1000], [1280, 900], [1024, 900]];
  const responsiveEvidence = [];
  for (const [width, height] of responsive) {
    await page.setViewportSize({ width, height });
    await page.goto("/home", { waitUntil: "domcontentloaded" });
    await expect(page.locator(".home-attention-row").first()).toBeVisible({ timeout: 15000 });
    const evidence = await page.evaluate(() => ({ width: innerWidth, horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1, stageCards: document.querySelectorAll(".home-stage-card").length, attentionRows: document.querySelectorAll(".home-attention-row").length }));
    responsiveEvidence.push(evidence);
    expect(evidence.horizontalOverflow).toBe(false);
    expect(evidence.stageCards).toBe(7);
    expect(evidence.attentionRows).toBeGreaterThan(0);
  }
  for (const route of ["/work", "/issues", "/billing", "/dashboard", "/notifications"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(400);
    await expect(page.locator("main")).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(route);
  }
  fs.mkdirSync(evidenceRoot, { recursive: true });
  fs.writeFileSync(path.join(evidenceRoot, "responsive-and-routes.json"), JSON.stringify({ responsive: responsiveEvidence, preservedRoutes: ["/work", "/issues", "/billing", "/dashboard", "/notifications"] }, null, 2));
});

test("Home navigation stays role-scoped for Business Development and Engineering", async ({ page }) => {
  await page.goto("/home", { waitUntil: "domcontentloaded" });
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.locator("nav[aria-label='Primary navigation'] .nav-item")).toHaveCount(6);
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Intake & Opportunity", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Contract & Mobilization", exact: true })).toBeVisible();
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.locator("nav[aria-label='Primary navigation'] .nav-item")).toHaveCount(7);
  await expect(page.getByRole("button", { name: "Design & Technical Delivery", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Handover & Closeout", exact: true })).toBeVisible();
});
