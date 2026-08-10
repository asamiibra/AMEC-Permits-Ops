import { test, expect } from "@playwright/test";

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("operating-guide-boundary-initialized")) {
      localStorage.clear();
      localStorage.setItem("permitops.locale", "ar-EG");
      sessionStorage.setItem("operating-guide-boundary-initialized", "true");
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

async function expectEnglishShell(page: import("@playwright/test").Page) {
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator(".global-language-switch")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("permitops.locale"))).toBeNull();
}

test("operational routes remain English/LTR and ignore stale global locale state", async ({ page }) => {
  for (const route of ["/work", "/permits", "/notifications", "/issues", "/opportunities", "/engineering-closeout", "/admin/discovery", "/admin/municipality", "/admin/go-live-readiness"]) {
    await page.goto(route);
    await expectEnglishShell(page);
    await expect(page.locator("body")).not.toContainText(/[\u0600-\u06FF]/);
  }
  await page.screenshot({ path: "../artifacts/bugfixes/operational-shell-english-ltr.png", fullPage: true });
});

test("Operating Guide toggles locally without changing the global shell", async ({ page }) => {
  await page.goto("/about");
  await expectEnglishShell(page);
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "en");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "ar-EG");
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
  await expectEnglishShell(page);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("permitops.operatingGuide.locale"))).toBe("ar-EG");
  await page.screenshot({ path: "../artifacts/bugfixes/operating-guide-ar-eg-local.png", fullPage: true });
  await page.reload();
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "ar-EG");
  await expectEnglishShell(page);
});

test("Operating Guide language control is isolated from Inputs & Go-Live", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await page.getByRole("button", { name: "Inputs & Go-Live" }).first().click();
  await expect(page.getByRole("dialog")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("dialog")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("dialog").getByRole("button", { name: "Switch to Arabic" })).toHaveCount(0);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
});

test("operational route remains English after refresh", async ({ page }) => {
  await page.goto("/notifications");
  await expectEnglishShell(page);
  await page.reload();
  await expectEnglishShell(page);
  await expect(page.getByRole("heading", { name: "Notifications", exact: true })).toBeVisible();
});
