import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const primaryRoutes = [
  "/home",
  "/work",
  "/proposals",
  "/contract-mobilization",
  "/engineering",
  "/billing",
  "/content-library",
];

const crossCuttingRoutes = ["/issues", "/notifications", "/owner-decisions"];

test.describe("real-stack UI product-surface closure", () => {
  test("uses the real API and exposes the seven canonical destinations", async ({ page, request }) => {
    const health = await request.get("/health");
    expect(health.ok()).toBeTruthy();
    const healthBody = await health.json();
    expect(healthBody.environment).toBe("TEST");
    expect(healthBody.synthetic_only).toBe(true);
    expect(healthBody.real_data_allowed).toBe(false);

    await page.goto("/home", { waitUntil: "networkidle" });
    const labels = await page.locator("nav[aria-label='Primary navigation'] .nav-item").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("aria-label")));
    expect(labels).toEqual(["Home", "AMEC Work", "Opportunities & Proposals", "Contract & Mobilization", "Projects & Delivery", "Billing & Finance", "Content Library"]);
    expect(labels.join(" ")).not.toMatch(/week|phase|source\s*\d+/i);
    await expect(page.locator("[data-runtime-environment='LOCAL_DEVELOPMENT']")).toBeVisible();
    const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((violation) => ["critical", "serious"].includes(violation.impact || ""));
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });

  test("keeps canonical and cross-cutting deep links connected to a real backend", async ({ page }) => {
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    for (const route of [...primaryRoutes, ...crossCuttingRoutes]) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("main").first()).toBeVisible();
      expect(new URL(page.url()).pathname, route).toBe(route);
    }
    expect(browserErrors).toEqual([]);
  });

  test("has no horizontal overflow at required responsive widths", async ({ page }) => {
    for (const width of [1440, 1280, 1024, 768, 390, 375]) {
      await page.setViewportSize({ width, height: width < 800 ? 844 : 900 });
      await page.goto("/home", { waitUntil: "domcontentloaded" });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      expect(overflow, `horizontal overflow at ${width}px`).toBeFalsy();
      if (width <= 700) await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
    }
  });

  test("re-evaluates administration access for the capability/persona matrix", async ({ page, request }) => {
    for (const role of ["PROCESS_CHAMPION", "COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"]) {
      const denied = await request.get("/api/admin/summary", { headers: { "X-Dev-Role": role } });
      expect(denied.status(), role).toBe(403);
    }
    const admin = await request.get("/api/admin/summary", { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    expect(admin.ok()).toBeTruthy();
    await page.goto("/work", { waitUntil: "domcontentloaded" });
    await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/home$/);
    await page.goto("/work", { waitUntil: "domcontentloaded" });
    await page.getByLabel("Persona").selectOption("SYSTEM_ADMIN");
    await page.goto("/admin", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "System administration", level: 3 })).toBeVisible();
  });

  test("has no serious or critical accessibility violations across the primary surface", async ({ page }) => {
    for (const route of primaryRoutes) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("main").first()).toBeVisible();
      await page.waitForTimeout(250);
      const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((violation) => ["critical", "serious"].includes(violation.impact || ""));
      expect(violations, `${route}: ${JSON.stringify(violations, null, 2)}`).toEqual([]);
    }
  });
});
