import { expect, test } from "@playwright/test";

test("AMEC Work exposes one Dashboard destination and the promoted current Dashboard", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "What needs attention", level: 2 })).toBeVisible();
  await expect(page.getByRole("link", { name: /Open Dashboard →/ })).toHaveCount(1);
  await expect(page.getByRole("link", { name: /Open Dashboard V2 →/ })).toHaveCount(0);

  await page.getByRole("link", { name: /Open Dashboard →/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toBeVisible();
  await expect(page.getByRole("link", { name: "Inputs & Go-Live" })).toHaveAttribute("href", "/dashboard/inputs-go-live");
});

test("/dashboard-v2 is a compatibility redirect to the current Dashboard", async ({ page }) => {
  await page.goto("/dashboard-v2?source=bookmark#forms");
  await expect(page).toHaveURL(/\/dashboard\?source=bookmark#forms$/);
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dashboard V2", level: 2 })).toHaveCount(0);
});

test("/dashboard-v2/inputs-go-live redirects to the single Inputs & Go-Live surface", async ({ page }) => {
  await page.goto("/dashboard-v2/inputs-go-live");
  await expect(page).toHaveURL(/\/dashboard\/inputs-go-live$/);
  await expect(page.getByRole("heading", { name: "Master Content Setup & Go-Live", level: 2 })).toBeVisible();
});
