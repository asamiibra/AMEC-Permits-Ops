import { test, expect } from "@playwright/test";

const adminRoutes = ["discovery", "config", "tier1", "tier2", "delivery", "thresholds", "corpus", "attachments-grids", "municipality", "spike", "adjudication", "analysis", "close", "baseline", "signoff", "confirmation", "business", "business-baseline", "privacy", "volume", "inquiries", "raid"];

test("shared readiness drawer exposes inputs, outputs, customer asks, and safe boundary", async ({ page }) => {
  await page.goto("/work");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Purpose")).toBeVisible();
  await expect(page.getByText("What this screen uses")).toBeVisible();
  await expect(page.getByText("What this screen produces")).toBeVisible();
  await expect(page.getByText("What we need from AMEC")).toBeVisible();
  await expect(page.getByText(/Current environment is a Synthetic Prototype/)).toBeVisible();
  await page.screenshot({ path: "../artifacts/production-readiness-ui/drawer-en.png", fullPage: true });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("readiness drawer stays English/LTR and has no Arabic toggle", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await expect(page.getByRole("dialog")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("dialog")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("dialog").getByRole("button", { name: "Switch to Arabic" })).toHaveCount(0);
  await expect(page.getByRole("dialog")).not.toContainText(/[\u0600-\u06FF]/);
  await page.screenshot({ path: "../artifacts/production-readiness-ui/drawer-english-ltr.png", fullPage: true });
});

test("admin can open the consolidated readiness view and export the filtered checklist", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.goto("/admin");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await page.getByRole("button", { name: "View all setup items" }).click();
  await expect(page).toHaveURL(/\/admin\/go-live-readiness$/);
  await expect(page.getByRole("heading", { name: "Go-Live Setup" }).last()).toBeVisible();
  await expect(page.getByText("Setup items", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../artifacts/production-readiness-ui/admin-readiness.png", fullPage: true });
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  await expect((await download).suggestedFilename()).toBe("permitops-go-live-setup.csv");
});

test("every implemented admin route keeps the shared drawer available", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  for (const route of adminRoutes) {
    await page.goto(`/admin/${route}`);
    await expect(page.getByRole("button", { name: "Inputs & Go-Live" }), route).toBeVisible();
  }
});

test("readiness copy is friendly while real human controls remain visible", async ({ page }) => {
  const forbidden = [/signed\s+scope/i, /stage\s*2\s+approval/i, /sign[- ]off\s+c/i, /\bg10\b/i, /formal\s+(?:production|build)\s+authorization/i, /technical\s+acceptance\s+signator/i, /formal\s+(?:sponsor|governance|change[- ]control)\s+approval/i, /formal\s+residual[- ]risk\s+acceptance/i, /governance\s+approval/i];
  await page.goto("/work");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("What we need from AMEC");
  for (const pattern of forbidden) await expect(drawer).not.toContainText(pattern);

  await page.keyboard.press("Escape");
  await page.goto("/permits/SYN-PROJ-0001/final-review");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await expect(page.getByRole("dialog")).toContainText("Package Approver");
  await expect(page.getByRole("dialog")).toContainText("Final Submitter");
  await page.keyboard.press("Escape");
  await page.goto("/permits/SYN-PROJ-0001/municipality-preparation");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await expect(page.getByRole("dialog")).toContainText("MFA");
  await page.keyboard.press("Escape");
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.goto("/admin/go-live-readiness");
  const pageText = await page.locator("body").innerText();
  for (const pattern of forbidden) expect(pageText).not.toMatch(pattern);
  expect(pageText).toMatch(/Commercial, contract, finance, and handover contacts/);
  expect(pageText).toMatch(/HUMAN_SEND|Human Send/);
});
