import { test, expect } from "@playwright/test";

test("real stack serves persona-aware issues and notifications without interception", async ({ page }) => {
  const intercepted: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/api/")) intercepted.push(request.url()); });
  await page.goto("/issues");
  await expect(page.getByRole("heading", { name: /Issues across AMEC work|Engineering issues/ })).toBeVisible();
  await expect(page.getByText(/Open issues|Open technical issues/).first()).toBeVisible({ timeout: 45_000 });
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByRole("heading", { name: "Engineering issues" })).toBeVisible();
  await page.goto("/notifications");
  await expect(page.getByRole("heading", { name: /Owner notifications|Engineering notifications/ })).toBeVisible();
  await expect(page.getByText("No delivery failures")).toBeVisible();
  expect(intercepted.length).toBeGreaterThan(0);
});
