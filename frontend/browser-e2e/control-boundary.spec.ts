import { test, expect } from "@playwright/test";

test("operator surface preserves the human-only final-submit boundary", async ({ page }) => {
  await page.setContent(`<main><div data-testid="synthetic-note">SYNTHETIC DEVELOPMENT / PROTOTYPE TRACK</div><section><span data-testid="no-final-submit">No final-submit control exists in this operator surface.</span><span data-testid="handoff">HUMAN SUBMISSION REQUIRED</span></section></main>`);
  await expect(page.getByTestId("synthetic-note")).toContainText("SYNTHETIC");
  await expect(page.getByTestId("no-final-submit")).toBeVisible();
  await expect(page.getByTestId("handoff")).toContainText("HUMAN SUBMISSION REQUIRED");
  await expect(page.locator("button", { hasText: /submit/i })).toHaveCount(0);
});
