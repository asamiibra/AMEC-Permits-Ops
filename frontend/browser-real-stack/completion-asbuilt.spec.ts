import { expect, test } from "@playwright/test";

test("Owner can open the Completion / As-Built workspace and see the explicit handoff gate", async ({ page }) => {
  await page.goto("/completion");
  await expect(page.getByRole("heading", { name: "Completion scopes" })).toBeVisible();
  await expect(page.getByText("Construction never auto-creates a Completion case.")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Start Completion" })).toBeVisible();
  await page.getByRole("button", { name: "Start Completion" }).click();
  await expect(page.getByRole("heading", { name: "Choose a completed construction scope" })).toBeVisible();
  await expect(page.getByText("Construction never auto-creates a Completion case. Start is an explicit Owner action.")).toBeVisible();
});
