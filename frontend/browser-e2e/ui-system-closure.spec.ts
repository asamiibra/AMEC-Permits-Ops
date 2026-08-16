import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");
const evidenceRoot = path.join(repoRoot, "artifacts", "ui-system-closure");

const screens = [
  { id: "dashboard-1440", route: "/dashboard", width: 1440, height: 1000 },
  { id: "proposal-register-1440", route: "/opportunities", width: 1440, height: 1000 },
  { id: "completion-empty-1440", route: "/completion", width: 1440, height: 1000 },
  { id: "engineering-1440", route: "/engineering", width: 1440, height: 1000 },
  { id: "issues-1440", route: "/issues", width: 1440, height: 1000 },
  { id: "admin-1440", route: "/admin", width: 1440, height: 1000 },
  { id: "dashboard-1920", route: "/dashboard", width: 1920, height: 1080 },
  { id: "dashboard-1280", route: "/dashboard", width: 1280, height: 900 },
  { id: "dashboard-1024", route: "/dashboard", width: 1024, height: 900 },
];

test("final UI system closure evidence has no visual or accessibility blockers", async ({ page }) => {
  fs.mkdirSync(evidenceRoot, { recursive: true });
  const results: Array<Record<string, unknown>> = [];
  for (const screen of screens) {
    await page.setViewportSize({ width: screen.width, height: screen.height });
    const consoleErrors: string[] = [];
    const onConsole = (message: import("@playwright/test").ConsoleMessage) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    };
    page.on("console", onConsole);
    await page.goto(screen.route, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);
    const metrics = await page.evaluate(() => {
      const compactDisclosure = document.querySelector(".compact-environment-badge");
      return {
        route: window.location.pathname,
        h1: document.querySelector("main h1")?.textContent?.trim() || "",
        h2: Array.from(document.querySelectorAll("main h2")).slice(0, 3).map((node) => node.textContent?.trim()),
        svgCount: document.querySelectorAll("svg").length,
        compactDisclosureHidden: !compactDisclosure || getComputedStyle(compactDisclosure).display === "none",
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        environmentVisible: document.body.innerText.includes("SYNTHETIC PROTOTYPE") && document.body.innerText.includes("Test data only") && document.body.innerText.includes("Simulated integrations"),
        pageHeaderCount: document.querySelectorAll("main h1, main h2").length,
      };
    });
    const axe = await new AxeBuilder({ page }).analyze();
    const seriousOrCritical = axe.violations.filter((item) => item.impact === "serious" || item.impact === "critical");
    await page.screenshot({ path: path.join(evidenceRoot, `${screen.id}.png`), fullPage: true });
    page.off("console", onConsole);
    results.push({ ...screen, ...metrics, consoleErrors, seriousOrCritical: seriousOrCritical.map((item) => item.id) });
    expect(metrics.horizontalOverflow, `${screen.id} has horizontal overflow`).toBe(false);
    expect(metrics.compactDisclosureHidden, `${screen.id} repeats the compact environment disclosure`).toBe(true);
    expect(metrics.environmentVisible, `${screen.id} hides environment truth`).toBe(true);
    expect(metrics.svgCount, `${screen.id} is missing the shared icon system`).toBeGreaterThan(0);
    expect(consoleErrors, `${screen.id} has console errors`).toEqual([]);
    expect(seriousOrCritical, `${screen.id} has serious/critical accessibility violations`).toEqual([]);
  }
  fs.writeFileSync(path.join(evidenceRoot, "visual-qa.json"), JSON.stringify({ screens: results }, null, 2));
});

test("visual closure preserves navigation, filter, table, and row-action contracts", async ({ page }) => {
  fs.mkdirSync(evidenceRoot, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);
  const sidebar = await page.locator(".nav-item").evaluateAll((nodes) =>
    nodes.map((node) => node.innerText.replace(/\s+/g, " ").trim()),
  );

  await page.goto("/proposals-contracts?view=proposals", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);
  const filterOptions = await page.locator(".filter-row .filter").allTextContents();
  const proposalHeaders = await page.locator(".table-panel table thead th").allTextContents();
  const proposalActionsBefore = await page.locator(".table-panel table tbody tr:first-child button").allTextContents();
  const selectableFilter = page.locator(".filter-row .filter").filter({ hasNotText: "All" }).first();
  if (await selectableFilter.count()) await selectableFilter.click();
  const routeAfterFilter = new URL(page.url()).pathname;
  const proposalHeadersAfter = await page.locator(".table-panel table thead th").allTextContents();
  const proposalActionsAfter = await page.locator(".table-panel table tbody tr:first-child button").allTextContents();
  const evidence = {
    sidebar,
    filterOptions: filterOptions.map((value) => value.trim()),
    routeBeforeFilter: "/proposals-contracts",
    routeAfterFilter,
    proposalHeaders: proposalHeaders.map((value) => value.trim()),
    proposalHeadersAfter: proposalHeadersAfter.map((value) => value.trim()),
    proposalActionsBefore: proposalActionsBefore.map((value) => value.trim()),
    proposalActionsAfter: proposalActionsAfter.map((value) => value.trim()),
    routePreserved: routeAfterFilter === "/proposals-contracts",
    tableHeadersPreserved: JSON.stringify(proposalHeaders) === JSON.stringify(proposalHeadersAfter),
  };
  fs.writeFileSync(path.join(evidenceRoot, "functional-parity.json"), JSON.stringify(evidence, null, 2));
  expect(evidence.routePreserved).toBe(true);
  expect(evidence.tableHeadersPreserved).toBe(true);
  expect(evidence.sidebar.length).toBeGreaterThan(0);
  expect(evidence.filterOptions.length).toBeGreaterThan(0);
});

test("final UI focus and 200 percent zoom affordances remain usable", async ({ page }) => {
  fs.mkdirSync(evidenceRoot, { recursive: true });
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);
  await page.keyboard.press("Tab");
  const focusEvidence = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement | null;
    if (!active) return { focused: false, focusIndicator: false, tag: "" };
    const style = getComputedStyle(active);
    return {
      focused: active !== document.body,
      focusIndicator: style.outlineStyle !== "none" && style.outlineWidth !== "0px" || style.boxShadow !== "none",
      tag: active.tagName,
    };
  });
  await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
  const zoomEvidence = await page.evaluate(() => {
    const header = document.querySelector("main h2")?.getBoundingClientRect();
    const primaryAction = document.querySelector("main button, main a")?.getBoundingClientRect();
    return {
      pageHeaderVisible: Boolean(header && header.width > 0 && header.height > 0),
      primaryActionVisible: Boolean(primaryAction && primaryAction.width > 0 && primaryAction.height > 0),
    };
  });
  const evidence = { focusEvidence, zoom200Evidence: zoomEvidence };
  fs.writeFileSync(path.join(evidenceRoot, "accessibility.json"), JSON.stringify(evidence, null, 2));
  expect(focusEvidence.focused).toBe(true);
  expect(focusEvidence.focusIndicator).toBe(true);
  expect(zoomEvidence.pageHeaderVisible).toBe(true);
  expect(zoomEvidence.primaryActionVisible).toBe(true);
});
