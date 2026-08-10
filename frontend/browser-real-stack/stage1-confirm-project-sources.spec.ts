import { expect, test } from "@playwright/test";

test("Stage 1 Confirm project & sources is a persisted real-stack command", async ({ page }) => {
  const apiRequests: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/api/")) apiRequests.push(`${request.method()} ${request.url()}`); });

  await page.goto("/proposals-contracts");
  await expect(page.getByRole("heading", { name: "Proposals & Contracts", level: 2 })).toBeVisible();
  const projectId = await page.evaluate(async () => (await (await fetch("/api/projects")).json())[0].id);
  await page.goto(`/proposals-contracts/${projectId}/project-and-sources`);
  await expect(page.getByRole("heading", { name: /Al Noor Villa/, level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm project & sources" })).toBeVisible();

  await page.getByRole("button", { name: "Confirm project & sources" }).click();
  await expect(page.getByText("Project & sources confirmed.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Verify project data" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("button", { name: "Verify project data" })).toBeVisible();
  await expect(page.getByText("STAGE 2 · VERIFY DATA", { exact: true })).toBeVisible();
  expect(apiRequests.some((value) => value.startsWith("POST") && value.includes("confirm-project-sources"))).toBeTruthy();
});
