import { expect, test } from "@playwright/test";

test("AMEC Work exposes one Content Library destination and the promoted current library", async ({ page }) => {
  await page.goto("/home");
  await expect(page.getByRole("heading", { name: "Prioritized work and lifecycle exceptions", level: 3 })).toBeVisible();
  await expect(page.getByRole("link", { name: /Open Content Library/ })).toHaveCount(1);
  await expect(page.getByRole("link", { name: /Open Dashboard V2 →/ })).toHaveCount(0);

  await page.getByRole("link", { name: /Open Content Library/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
  await expect(page.getByTestId("current-dashboard")).toHaveAttribute("data-dashboard-root", "v2-evolution");
  await expect(page.getByTestId("dashboard-governance-overview")).toBeVisible();
  await expect(page.getByTestId("dashboard-library-navigation")).toBeVisible();
  await expect(page.getByTestId("dashboard-source-authority-panel")).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toBeVisible();
  await expect(page.getByRole("link", { name: "Inputs & Go-Live" })).toHaveAttribute("href", "/dashboard/inputs-go-live");
});

test("/dashboard-v2 is a compatibility redirect to the current Content Library", async ({ page }) => {
  await page.goto("/dashboard-v2?source=bookmark#forms");
  await expect(page).toHaveURL(/\/dashboard\?source=bookmark#forms$/);
  await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dashboard V2", level: 2 })).toHaveCount(0);
});

test("/dashboard-v2/inputs-go-live redirects to the single Inputs & Go-Live surface", async ({ page }) => {
  await page.goto("/dashboard-v2/inputs-go-live");
  await expect(page).toHaveURL(/\/dashboard\/inputs-go-live$/);
  await expect(page.getByRole("heading", { name: "Master Content Setup & Go-Live", level: 2 })).toBeVisible();
});
