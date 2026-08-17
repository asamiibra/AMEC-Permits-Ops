import { expect, test } from "@playwright/test";

test.describe("Owner Decision Center canonical closure", () => {
  test("shows one truthful 50-decision register and computed go-live blockers", async ({ page }) => {
    await page.goto("/admin/owner-decisions");
    await expect(page.getByRole("heading", { name: "One Owner Decision Register" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /decision\(s\)/ }).first()).toBeVisible();
    await expect(page.getByText("Blocked", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Real Synology remains a technical fact", { exact: false })).toBeVisible();
    await expect(page.getByText("P0 blockers", { exact: true })).toBeVisible();
    await expect(page.getByText("External technical", { exact: true })).toBeVisible();
  });

  test("Owner confirmation is audited, runtime-read back, and technical facts stay protected", async ({ page, request }) => {
    await page.goto("/admin/owner-decisions");
    await page.getByRole("button", { name: /Master Category Semantics/ }).click();
    const applyResponse = page.waitForResponse((response) => response.ok() && response.request().method() === "POST" && response.url().endsWith("/api/owner-decisions/MASTER_CATEGORY_SEMANTICS/actions"));
    const refreshResponse = page.waitForResponse((response) => response.ok() && response.request().method() === "GET" && response.url().endsWith("/api/owner-decisions"));
    await page.getByRole("button", { name: "Confirm recommended default" }).click();
    const applyPayload = await (await applyResponse).json();
    expect(applyPayload).toMatchObject({ runtime: { apply_state: "APPLIED" } });
    await refreshResponse;
    const confirmedDecision = page.getByRole("button", { name: /Master Category Semantics/ });
    await expect(confirmedDecision).toContainText("Owner Confirmed", { timeout: 45_000 });
    await confirmedDecision.click();
    await expect(page.getByRole("heading", { name: "Master Category Semantics", level: 3 })).toBeVisible();
    await expect(page.getByText("Applied", { exact: true }).first()).toBeVisible();
    const denied = await request.post("/api/owner-decisions/REAL_SYNOLOGY_CONNECTION/actions", { headers: { "X-Dev-Role": "OWNER_SPONSOR" }, data: { action: "confirm_default" } });
    expect(denied.status()).toBe(409);
    const technical = await page.request.get("/api/owner-decisions/REAL_SYNOLOGY_CONNECTION");
    expect((await technical.json()).status).toBe("EXTERNAL_TECHNICAL_BLOCK");
  });
});
