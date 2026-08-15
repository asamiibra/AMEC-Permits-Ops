import { expect, test } from "@playwright/test";

const owner = { "X-Dev-Role": "SYSTEM_ADMIN" };

test("Proposal register counts reconcile with visible rows and valid opens are renderable", async ({ page, request }) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) browserErrors.push(message.text());
  });
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  const response = await request.get("/api/bd/proposals", { headers: owner });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.predicate_version).toBe("bd-proposal-register-v2");
  expect(body.lane_counts.ALL).toBe(body.items.length);
  for (const lane of ["NEED_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"]) {
    const filtered = await request.get(`/api/bd/proposals?lane=${lane}`, { headers: owner });
    const filteredBody = await filtered.json();
    expect(filteredBody.lane_counts[lane]).toBe(filteredBody.items.length);
  }
  expect(body.items.length).toBeGreaterThan(0);

  await page.goto("/opportunities");
  await expect(page.getByRole("heading", { name: "Proposal Register", level: 2 })).toBeVisible();
  await expect(page.getByRole("tab", { name: new RegExp(`All\\s*${body.lane_counts.ALL}`) })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open →" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Open →" }).first().click();
  await expect(page).toHaveURL(/\/opportunities\/[0-9a-f-]+$/);
  await expect(page.getByText("ProposalOps could not render this screen", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Managed in Dashboard", level: 3 })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Managed in Dashboard", level: 3 })).toBeVisible();

  for (const item of body.items.slice(1, 3)) {
    await page.goto(`/opportunities/${item.id}`);
    await expect(page.getByRole("heading", { name: "Managed in Dashboard", level: 3 })).toBeVisible();
    await expect(page.getByText("ProposalOps could not render this screen", { exact: false })).toHaveCount(0);
  }

  await page.goto("/opportunities/not-a-real-proposal");
  await expect(page.getByText("Could not load this Proposal.", { exact: false })).toBeVisible();
  await expect(page.getByText("ProposalOps could not render this screen", { exact: false })).toHaveCount(0);
  expect(browserErrors).toEqual([]);
});

test("New Proposal source cards select and render every source-specific panel", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.goto("/opportunities/new");
  await expect(page.getByRole("heading", { name: "New Proposal Intake", level: 2 })).toBeVisible();
  for (const label of ["Tender Email", "Tender Document", "Tender Photo / Image", "Client Information"]) {
    await page.getByRole("button", { name: new RegExp(`^${label} Choose`) }).click();
    await expect(page.getByRole("heading", { name: `${label} intake`, level: 4 })).toBeVisible();
    await expect(page.getByRole("button", { name: `Create Proposal & Add ${label}` })).toBeVisible();
    await expect(page.getByLabel(`${label} source file`)).toBeVisible();
  }
  expect(await page.locator("button[aria-pressed=\"true\"]").count()).toBe(1);
});
