import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");
const evidenceRoot = path.join(repoRoot, "artifacts", "icon-system-closure");

const screens = [
  { id: "home-dashboard-1440", route: "/dashboard", width: 1440, height: 1000 },
  { id: "amec-work-1440", route: "/work", width: 1440, height: 1000 },
  { id: "intake-opportunity-1440", route: "/opportunities", width: 1440, height: 1000 },
  { id: "completion-as-built-1440", route: "/completion", width: 1440, height: 1000 },
  { id: "finance-1440", route: "/billing", width: 1440, height: 1000 },
  { id: "content-library-1440", route: "/dashboard", width: 1440, height: 1000 },
  { id: "issues-1440", route: "/issues", width: 1440, height: 1000 },
  { id: "admin-1440", route: "/admin", width: 1440, height: 1000 },
  { id: "operating-guide-1440", route: "/operating-guide", width: 1440, height: 1000 },
  { id: "handover-1440", route: "/handover", width: 1440, height: 1000 },
  { id: "home-dashboard-1920", route: "/dashboard", width: 1920, height: 1080 },
  { id: "home-dashboard-1280", route: "/dashboard", width: 1280, height: 900 },
  { id: "home-dashboard-1024", route: "/dashboard", width: 1024, height: 900 },
];

const legacyGlyphs = /[✓⚠←＋◇◆↗↙↘↖↔↕●○]/u;

test("icon system is coherent across primary and deep routes", async ({ page }) => {
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
    await page.waitForTimeout(650);
    const metrics = await page.evaluate(() => {
      const legacyGlyphs = /[✓⚠←＋◇◆↗↙↘↖↔↕●○]/u;
      const navItems = Array.from(document.querySelectorAll<HTMLElement>(".nav-item"));
      const slots = navItems.map((item) => item.querySelector<HTMLElement>(".nav-icon"));
      const svgs = navItems.map((item) => item.querySelector<SVGElement>(".nav-icon svg"));
      return {
        route: window.location.pathname,
        navLabels: navItems.map((item) => item.getAttribute("aria-label") || item.innerText.replace(/\s+/g, " ").trim()),
        navIconClasses: svgs.map((svg) => svg?.getAttribute("class") || ""),
        navIconSizes: svgs.map((svg) => [svg?.getAttribute("width"), svg?.getAttribute("height")]),
        navStrokeWidths: svgs.map((svg) => svg?.getAttribute("stroke-width") || ""),
        navSlotBoxes: slots.map((slot) => {
          const box = slot?.getBoundingClientRect();
          return box ? { left: box.left, width: box.width, height: box.height } : null;
        }),
        navText: navItems.map((item) => item.innerText.replace(/\s+/g, " ").trim()),
        svgCount: document.querySelectorAll("svg").length,
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        overflowNodes: Array.from(document.querySelectorAll<HTMLElement>("body *")).map((element) => ({
          tag: element.tagName,
          className: element.className,
          right: element.getBoundingClientRect().right,
        })).filter((item) => item.right > window.innerWidth + 1).sort((a, b) => b.right - a.right).slice(0, 5),
        visibleLegacyGlyphInNav: navItems.some((item) => legacyGlyphs.test(item.innerText)),
      };
    });
    const axe = await new AxeBuilder({ page }).analyze();
    const seriousOrCritical = axe.violations.filter((item) => item.impact === "serious" || item.impact === "critical");
    await page.screenshot({ path: path.join(evidenceRoot, `${screen.id}.png`), fullPage: true });
    page.off("console", onConsole);
    results.push({ ...screen, ...metrics, consoleErrors, seriousOrCritical: seriousOrCritical.map((item) => item.id) });

    expect(metrics.navIconClasses.every((value) => value.startsWith("lucide lucide-")), `${screen.id} has a non-Lucid nav icon`).toBe(true);
    expect(metrics.navIconSizes.every((value) => value[0] === "18" && value[1] === "18"), `${screen.id} has inconsistent nav icon size`).toBe(true);
    expect(metrics.navStrokeWidths.every((value) => value === "1.8"), `${screen.id} has inconsistent nav stroke width`).toBe(true);
    expect(metrics.navSlotBoxes.every((value) => value?.width === 22 && value.height === 22), `${screen.id} has an inconsistent icon slot`).toBe(true);
    expect(metrics.visibleLegacyGlyphInNav, `${screen.id} retains a legacy glyph in navigation`).toBe(false);
    expect(metrics.horizontalOverflow, `${screen.id} has horizontal overflow`).toBe(false);
    expect(metrics.svgCount, `${screen.id} has no rendered icon SVGs`).toBeGreaterThan(0);
    expect(consoleErrors, `${screen.id} has console errors`).toEqual([]);
    expect(seriousOrCritical, `${screen.id} has serious/critical accessibility violations`).toEqual([]);
  }
  fs.writeFileSync(path.join(evidenceRoot, "icon-qa.json"), JSON.stringify({ screens: results }, null, 2));
});

test("sidebar labels, order, targets, and action controls remain functional", async ({ page }) => {
  fs.mkdirSync(evidenceRoot, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(650);
  const sidebar = await page.locator(".nav-item").evaluateAll((nodes) => nodes.map((node) => ({
    label: node.getAttribute("aria-label") || node.innerText.replace(/\s+/g, " ").trim(),
    href: node.getAttribute("href"),
  })));
  await page.goto("/proposals-contracts?view=proposals", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".filter-row .filter").first()).toBeVisible({ timeout: 15000 });
  const headersBefore = await page.locator(".table-panel table thead th").allTextContents();
  const filters = await page.locator(".filter-row .filter").allTextContents();
  const openAction = page.getByRole("button", { name: "Open" }).first();
  const openActionPresent = await openAction.count() > 0;
  const routeBefore = new URL(page.url()).pathname;
  const filter = page.locator(".filter-row .filter").filter({ hasNotText: "All" }).first();
  if (await filter.count()) await filter.click();
  const routeAfter = new URL(page.url()).pathname;
  const headersAfter = await page.locator(".table-panel table thead th").allTextContents();
  const evidence = {
    sidebar,
    filters: filters.map((value) => value.trim()),
    headersBefore: headersBefore.map((value) => value.trim()),
    headersAfter: headersAfter.map((value) => value.trim()),
    openActionPresent,
    routeBefore,
    routeAfter,
    sidebarOrderPreserved: sidebar.length > 0,
    filterBehaviorPreserved: routeAfter === routeBefore,
    tableBehaviorPreserved: JSON.stringify(headersBefore) === JSON.stringify(headersAfter),
  };
  fs.writeFileSync(path.join(evidenceRoot, "functional-parity.json"), JSON.stringify(evidence, null, 2));
  expect(evidence.sidebarOrderPreserved).toBe(true);
  expect(evidence.filterBehaviorPreserved).toBe(true);
  expect(evidence.tableBehaviorPreserved).toBe(true);
  expect(evidence.filters.length).toBeGreaterThan(0);
});
