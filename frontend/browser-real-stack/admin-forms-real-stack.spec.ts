import { expect, test } from "@playwright/test";

async function saveNewForm(page: import("@playwright/test").Page, ref: string, body: string) {
  await page.getByRole("button", { name: "New Form" }).click();
  await page.getByLabel("Title / Name").fill(`Canonical ${ref}`);
  await page.getByLabel("Reference").fill(ref);
  await page.getByLabel("Description").fill("One canonical Form record shared by Dashboard and Administration.");
  await page.getByLabel("File").setInputFiles({ name: `${ref}.txt`, mimeType: "text/plain", buffer: Buffer.from(body) });
  await page.getByRole("button", { name: "Save and verify" }).click();
  await expect(page.getByText(ref, { exact: true })).toBeVisible();
}

async function saveVersion(page: import("@playwright/test").Page, row: import("@playwright/test").Locator, body: string, reason: string) {
  await row.getByRole("button", { name: "Modify" }).click();
  await page.getByLabel("Change reason").fill(reason);
  await page.getByLabel("File").setInputFiles({ name: `${reason.replaceAll(" ", "-")}.txt`, mimeType: "text/plain", buffer: Buffer.from(body) });
  await page.getByRole("button", { name: "Save new version" }).click();
}

async function downloadHistoryVersion(page: import("@playwright/test").Page, index: number) {
  const download = page.getByRole("button", { name: "Download" }).nth(index);
  const event = page.waitForEvent("download");
  await download.click();
  const file = await event;
  const stream = await file.createReadStream();
  if (!stream) throw new Error("Download stream unavailable");
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

test("Administration Forms and Dashboard are two doors into one canonical library", async ({ page }) => {
  const ref = `AF-${Date.now().toString(36)}`;
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administration", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Forms/ })).toBeVisible();
  await page.getByRole("button", { name: /^Forms/ }).click();
  await expect(page.getByRole("heading", { name: "Forms", level: 2 })).toBeVisible();
  await saveNewForm(page, ref, "admin-v1");

  await page.goto("/dashboard");
  const dashboardRow = page.getByRole("row").filter({ hasText: ref });
  await expect(dashboardRow).toContainText("v1");
  await saveVersion(page, dashboardRow, "dashboard-v2", "Dashboard version two");
  await expect(page.getByRole("row").filter({ hasText: ref })).toContainText("v2");

  await page.goto("/admin/forms");
  const adminRow = page.getByRole("row").filter({ hasText: ref });
  await expect(adminRow).toContainText("v2");
  await adminRow.getByRole("button", { name: "Version History" }).click();
  await expect(page.getByText("IMMUTABLE HISTORY")).toBeVisible();
  expect(await downloadHistoryVersion(page, 1)).toEqual(Buffer.from("admin-v1"));
  expect(await downloadHistoryVersion(page, 0)).toEqual(Buffer.from("dashboard-v2"));
  await page.getByRole("button", { name: "×" }).click();

  await saveVersion(page, adminRow, "admin-v3", "Administration version three");
  await expect(page.getByRole("row").filter({ hasText: ref })).toContainText("v3");

  await page.goto("/dashboard");
  const finalRow = page.getByRole("row").filter({ hasText: ref });
  await expect(finalRow).toContainText("v3");
  await finalRow.getByRole("button", { name: "Version History" }).click();
  await expect(page.getByText("IMMUTABLE HISTORY")).toBeVisible();
  expect(await page.getByRole("button", { name: "Download" }).count()).toBe(3);
  expect(await downloadHistoryVersion(page, 2)).toEqual(Buffer.from("admin-v1"));
  expect(await downloadHistoryVersion(page, 1)).toEqual(Buffer.from("dashboard-v2"));
});

test("Administration remains Owner-only for the Forms management surface", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await page.goto("/admin/forms");
  await expect(page).toHaveURL(/\/work$/);
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await page.goto("/admin/forms");
  await expect(page).toHaveURL(/\/work$/);
});
