import { expect, test } from "@playwright/test";

const owner = { "X-Dev-Role": "OWNER_SPONSOR" };

test("Billing V2 real stack renders project-safe invoice context and communication history", async ({ page }) => {
  const list = await page.request.get("/api/billing/invoices", { headers: owner });
  expect(list.ok()).toBeTruthy();
  const body = await list.json();
  expect(body).toHaveProperty("items");
  expect(body).toHaveProperty("lanes");
  expect(body.items.length).toBeGreaterThan(0);

  const invoiceId = body.items[0].invoice.id;
  const communications = await page.request.get(`/api/billing/invoices/${invoiceId}/communications`, { headers: owner });
  expect(communications.ok()).toBeTruthy();
  expect(await communications.json()).toEqual(expect.objectContaining({ communication_state: expect.any(String), deliveries: expect.any(Array), acknowledgments: expect.any(Array) }));

  await page.goto("/billing/invoices");
  await expect(page.getByRole("heading", { name: "Billing & Invoice", level: 2 })).toBeVisible();
  await expect(page.getByRole("table", { name: "Invoices" })).toBeVisible();
  await page.getByRole("button", { name: "Open →" }).first().click();
  await expect(page.getByRole("heading", { name: /INV-|Not allocated/ })).toBeVisible();
  await expect(page.getByText("COMMUNICATION HISTORY", { exact: true })).toBeVisible();
  await expect(page.getByText(/Delivery, acknowledgment, approval, and payment remain separate/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/accounting journal|financial settlement performed/i);
});
