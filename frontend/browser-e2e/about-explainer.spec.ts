import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/projects" ? [] : path === "/api/applications" ? [] : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" } : {};
    await route.fulfill({ json: body });
  });
});

test("English Guide tells the full lifecycle story", async ({ page }) => {
  await page.goto("/operating-guide");
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: /ProposalOps helps AMEC move work from tender/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "The AMEC workflow" })).toBeVisible();
  await expect(page.locator(".about-lifecycle-step")).toHaveCount(7);
  await expect(page.getByText(/Proposal → Contract → Permit/).first()).toBeVisible();
  await expect(page.getByText("Proceed means Proposal Intake has enough verified information to move into Engineering Proposal Preparation.")).toBeVisible();
  await expect(page.locator("main.about-page")).not.toContainText(/PermitOps|Permit Preparer|four assistants|Resume permit work|E7|persona projection|HUMAN_SEND|MISSING_DOCUMENT/);
});

test("English Guide explains core surfaces, source control, and human boundary", async ({ page }) => {
  await page.goto("/operating-guide");
  await expect(page.getByText("AMEC Work", { exact: true })).toBeVisible();
  await expect(page.getByText("Issues", { exact: true })).toBeVisible();
  await expect(page.getByText("Notifications", { exact: true })).toBeVisible();
  await expect(page.getByText("One shared truth", { exact: true })).toBeVisible();
  await expect(page.getByText("Final submission stays human-controlled.", { exact: true })).toBeVisible();
  await expect(page.getByText("Synthetic prototype truth", { exact: true })).toBeVisible();
});

test("Arabic switch preserves meaning and enables RTL", async ({ page }) => {
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "العربي" }).click();
  const main = page.locator("main.about-page");
  await expect(main).toHaveAttribute("lang", "ar-EG");
  await expect(main).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "دورة عمل AMEC" })).toBeVisible();
  await expect(page.getByText("التقديم النهائي بشري.", { exact: true })).toBeVisible();
  expect(await main.locator('bdi[dir="ltr"]').count()).toBeGreaterThan(15);
});

test("language control is accessible and does not navigate away", async ({ page }) => {
  await page.goto("/operating-guide");
  await expect(page.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.getByRole("button", { name: "العربي" })).toHaveAttribute("aria-pressed", "true");
  await expect(page).toHaveURL(/\/operating-guide$/);
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "ltr");
});

test("Guide navigation links reach existing routes", async ({ page }) => {
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "Back to AMEC Work" }).click();
  await expect(page).toHaveURL(/\/work$/);
  await page.goto("/operating-guide");
  await page.getByRole("button", { name: "Open Proposals & Contracts" }).click();
  await expect(page).toHaveURL(/\/proposals-contracts$/);
});

test("mobile English and Arabic Guide have no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/operating-guide");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await page.getByRole("button", { name: "العربي" }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
});
