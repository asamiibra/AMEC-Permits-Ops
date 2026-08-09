import { test, expect } from "@playwright/test";

const projects = [{ id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" }];

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("permitops-role")) sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN");
  });
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/projects" ? projects : path === "/api/applications" ? [{ id: "a-0142", project_id: "p-0142", external_request_number: "GHCE-APP-0142", application_status: "DRAFT", repetition_count: 0 }] : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" } : {};
    await route.fulfill({ json: body });
  });
});

test("primary routes render a controlled shell and truthful environment label", async ({ page }) => {
  for (const [path, heading] of [["/work", "Resume permit work"], ["/permits", "Permits"], ["/opportunities", "Opportunities"], ["/engineering-closeout", "Engineering & Closeout"], ["/reviews", "Reviews"], ["/issues", "Issues"], ["/notifications", "Notifications"], ["/about", "PermitOps helps AMEC"]] as const) {
    await page.goto(path);
    await expect(page.locator("main").getByRole("heading", { name: new RegExp(heading) }).last()).toBeVisible();
    await expect(page.getByText("SYNTHETIC PROTOTYPE", { exact: true }).last()).toBeVisible();
  }
});

test("browser back and forward keep the React route state synchronized", async ({ page }) => {
  await page.goto("/work");
  await page.getByRole("navigation").getByRole("button", { name: "Permits" }).click();
  await expect(page.getByRole("heading", { name: "Permits" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("heading", { name: "Permits" })).toBeVisible();
});

test("unknown routes fall back to My Work without a blank screen", async ({ page }) => {
  await page.goto("/this-route-does-not-exist");
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
  await expect(page.locator("main")).toBeVisible();
});

test("About language preference survives a refresh without changing business route", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await page.reload();
  await expect(page.locator("main.about-page")).toHaveAttribute("lang", "ar-EG");
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
});

test("role filtering changes visible business navigation without granting admin access", async ({ page }) => {
  await page.goto("/work");
  await page.getByRole("combobox", { name: "Role" }).selectOption("PERMIT_PREPARER");
  await expect(page.getByRole("navigation").getByRole("button", { name: "Issues" })).toBeVisible();
  await expect(page.getByRole("navigation").getByRole("button", { name: "Reviews" })).toHaveCount(0);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/work$/);
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
});

test("primary shell exposes human submission boundary and no final-submit control", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByText("HUMAN SUBMISSION REQUIRED").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /final submit|submit application/i })).toHaveCount(0);
});
