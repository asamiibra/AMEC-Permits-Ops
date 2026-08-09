import { test, expect } from "@playwright/test";

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("language-toggle-test-initialized")) {
      localStorage.clear();
      sessionStorage.setItem("language-toggle-test-initialized", "true");
    }
    sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN");
  });
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/projects" ? [project]
      : path === "/api/applications" ? [{ id: "a-0142", project_id: project.id, external_request_number: "GHCE-APP-0142", application_status: "DRAFT", repetition_count: 0 }]
      : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" }
      : path === "/api/discovery/decisions" ? []
      : {};
    await route.fulfill({ json: body });
  });
});

async function expectRootLocale(page: import("@playwright/test").Page, locale: "en" | "ar-EG") {
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await expect(page.locator("html")).toHaveAttribute("dir", locale === "ar-EG" ? "rtl" : "ltr");
  await expect(page.locator("#root")).toHaveAttribute("dir", locale === "ar-EG" ? "rtl" : "ltr");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("permitops.locale"))).toBe(locale);
}

async function toggle(page: import("@playwright/test").Page, locale: "en" | "ar-EG") {
  await page.locator(".global-language-switch").click();
  await expectRootLocale(page, locale);
}

test("Notifications EN → AR → EN restores the full shell and captures proof", async ({ page }) => {
  await page.goto("/notifications");
  await expect(page.getByRole("heading", { name: "Notifications & delivery" })).toBeVisible();
  await expectRootLocale(page, "en");
  await page.screenshot({ path: "../artifacts/bugfixes/language-toggle-notifications-en-before.png", fullPage: true });

  await toggle(page, "ar-EG");
  await expect(page.getByRole("button", { name: "Switch to English" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "الإشعارات والتسليم" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/bugfixes/language-toggle-notifications-ar-after.png", fullPage: true });

  await toggle(page, "en");
  await expect(page.getByRole("heading", { name: "Notifications & delivery" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Switch to Arabic" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/bugfixes/language-toggle-notifications-en-restored.png", fullPage: true });
  const sidebar = await page.locator(".sidebar").boundingBox();
  expect(sidebar?.x).toBe(0);
});

test("Permit workspace preserves route, stage, and language across five toggles", async ({ page }) => {
  const route = "/permits/p-0142/verify-data";
  await page.goto(route);
  await expect(page).toHaveURL(new RegExp("/permits/p-0142/verify-data$"));
  await expectRootLocale(page, "en");
  for (const locale of ["ar-EG", "en", "ar-EG", "en", "ar-EG"] as const) {
    await toggle(page, locale);
    await expect(page).toHaveURL(new RegExp("/permits/p-0142/verify-data$"));
  }
  await expect(page.getByText("مراجعة البيانات").first()).toBeVisible();
  await toggle(page, "en");
  await expect(page).toHaveURL(new RegExp("/permits/p-0142/verify-data$"));
  await expect(page.getByText("Verify Data").first()).toBeVisible();
});

test("About and Inputs & Go-Live stay synchronized while open", async ({ page }) => {
  await page.goto("/about");
  await toggle(page, "ar-EG");
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "ar-EG");
  await page.getByRole("button", { name: "المدخلات والتشغيل" }).click();
  await expect(page.getByRole("dialog")).toHaveAttribute("dir", "rtl");
  await toggle(page, "en");
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("dialog")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("dialog")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("dialog").getByRole("button", { name: "Switch to Arabic" })).toBeVisible();
});

test("operational routes all follow the global locale and refresh preserves English", async ({ page }) => {
  for (const route of ["/work", "/permits", "/notifications", "/issues", "/opportunities", "/engineering-closeout", "/admin/discovery", "/admin/municipality", "/admin/go-live-readiness"]) {
    await page.goto(route);
    await expectRootLocale(page, "en");
    await toggle(page, "ar-EG");
    await toggle(page, "en");
    await expect(page).toHaveURL(new RegExp(`${route.replaceAll("/", "\\/")}$`));
  }
  await page.goto("/notifications");
  await toggle(page, "ar-EG");
  await page.reload();
  await expectRootLocale(page, "ar-EG");
  await toggle(page, "en");
  await page.reload();
  await expectRootLocale(page, "en");
  await expect(page.getByRole("heading", { name: "Notifications & delivery" })).toBeVisible();
});
