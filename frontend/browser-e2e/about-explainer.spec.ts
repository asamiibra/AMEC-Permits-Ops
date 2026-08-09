import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/projects" ? [] : path === "/api/applications" ? [] : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" } : {};
    await route.fulfill({ json: body });
  });
});

test("About page is reachable from the My Work landing surface", async ({ page }) => {
  await page.goto("/work");
  await page.getByRole("button", { name: "About PermitOps" }).click();
  await expect(page.locator("main.about-page")).toBeVisible();
});

test("English explainer has the business purpose and current MVP heading", async ({ page }) => {
  await page.goto("/about");
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: /PermitOps helps AMEC/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Capabilities available in the current MVP" })).toBeVisible();
});

test("English explainer exposes the eight-stage lifecycle", async ({ page }) => {
  await page.goto("/about");
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(8);
  await expect(page.locator(".about-lifecycle")).toHaveAttribute("aria-label", "Eight lifecycle stages");
});

test("business visuals are present", async ({ page }) => {
  await page.goto("/about");
  await expect(page.locator(".about-hero-visual")).toBeVisible();
  await expect(page.locator(".about-loop")).toBeVisible();
  await expect(page.locator(".about-data-flow")).toBeVisible();
  await expect(page.locator(".about-architecture-layers")).toBeVisible();
});

test("feature status taxonomy is truthful", async ({ page }) => {
  await page.goto("/about");
  const broader = page.locator(".about-broader");
  await expect(broader).toBeVisible();
  await expect(broader.getByText("Foundation only", { exact: true }).first()).toBeVisible();
  await expect(broader.getByText("Implemented in prototype", { exact: true }).first()).toBeVisible();
  await expect(broader.getByText("Planned / pending scope", { exact: true }).first()).toBeVisible();
});

test("English feature evidence is visible", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText("Evidence:", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("Project model", { exact: false })).toBeVisible();
});

test("Arabic switch sets Egyptian Arabic and true RTL", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  const main = page.locator("main.about-page");
  await expect(main).toHaveAttribute("lang", "ar-EG");
  await expect(main).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "ليه PermitOps موجود؟" })).toBeVisible();
});

test("Arabic technical terms are isolated in bdi elements", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  const terms = page.locator("main.about-page[dir=rtl] bdi[dir=ltr]");
  await expect(terms).toHaveCount(await terms.count());
  expect(await terms.count()).toBeGreaterThan(15);
  const tags = await terms.evaluateAll(elements => elements.map(element => element.tagName));
  expect(new Set(tags)).toEqual(new Set(["BDI"]));
});

test("Arabic Bidi terms use CSS isolation", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  const style = await page.locator("main.about-page[dir=rtl] bdi[dir=ltr]").first().evaluate(element => ({ direction: getComputedStyle(element).direction, unicodeBidi: getComputedStyle(element).unicodeBidi }));
  expect(style.direction).toBe("ltr");
  expect(style.unicodeBidi).toContain("isolate");
});

test("Arabic lifecycle remains eight logical stages", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(8);
  await expect(page.locator(".about-lifecycle")).toHaveAttribute("aria-label", "المراحل الثمانية لسير العمل");
});

test("language controls expose pressed state", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.getByRole("button", { name: "العربي" })).toHaveAttribute("aria-pressed", "true");
});

test("human decision boundary is explicit in English", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText("AI assists; people decide", { exact: true })).toBeVisible();
  await expect(page.getByText("No machine final submit", { exact: true })).toBeVisible();
  await expect(page.getByText("No generic browser agent", { exact: true })).toBeVisible();
});

test("human decision boundary is explicit in Arabic", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.getByText("إيه اللي PermitOps مش بيعمله؟", { exact: true })).toBeVisible();
  await expect(page.getByText("مفيش Final Submit آلي", { exact: true })).toBeVisible();
});

test("About page has accessible section headings and controls", async ({ page }) => {
  await page.goto("/about");
  await expect(page.locator("main.about-page").getByRole("heading", { level: 1 })).toHaveCount(1);
  await expect(page.getByRole("group", { name: "Language" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Back to My Work" })).toBeVisible();
});

test("About page preserves the My Work call to action", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "Open My Work" }).click();
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
});

test("About page preserves the permit navigation call to action", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "View Permits" }).click();
  await expect(page.getByRole("heading", { name: "Permits" })).toBeVisible();
});

test("mobile About page has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/about");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
  await expect(page.locator("main.about-page")).toBeVisible();
});

test("mobile Arabic About page retains RTL and no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
});

test("About page keeps prototype and external-boundary messaging visible", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText("SYNTHETIC PROTOTYPE", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("No production portal writes", { exact: false })).toBeVisible();
});
