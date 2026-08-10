import { expect, test } from "@playwright/test";

type Issue = { id: string; title: string; domain: string; deep_link: string; actionability: string; cta_label?: string };

const issuesFor = async (page: any, persona: string): Promise<Issue[]> => (await (await page.request.get(`/api/issues?persona=${persona}`)).json()).issues;

test("Issues deep-link to existing context with focus, refresh, and clean copy", async ({ page }) => {
  await page.goto("/issues");
  const ownerIssues = await issuesFor(page, "OWNER");
  expect(ownerIssues.length).toBeGreaterThanOrEqual(7);
  expect(ownerIssues.every((item) => item.deep_link.includes("?issue=") && !item.deep_link.startsWith("/issues/"))).toBe(true);

  for (const issue of ownerIssues) {
    await page.goto(issue.deep_link);
    await expect(page.getByText("OPENED FROM ISSUE", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: issue.title, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to Issues", exact: true })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/PERSONA_FIXTURE|synthetic:\/\/|CANONICAL_PROJECT_SOR|READ_BACK_VERIFIED|Open record|quotation revision/i);
    await page.reload();
    await expect(page.getByText("OPENED FROM ISSUE", { exact: true })).toBeVisible();
  }
});

test("BD and Engineering deep-links enforce actionable versus context-only targets", async ({ page }) => {
  await page.goto("/issues");
  const bdIssues = await issuesFor(page, "BUSINESS_DEVELOPMENT");
  const bdTechnical = bdIssues.find((item) => item.domain === "PROPOSAL_TECHNICAL");
  const bdCommercial = bdIssues.find((item) => item.domain === "PROPOSAL_COMMERCIAL");
  expect(bdTechnical?.actionability).toBe("CONTEXT_ONLY");
  expect(bdCommercial?.actionability).toBe("ACTIONABLE");

  await page.goto("/issues");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByRole("heading", { name: "Commercial & project issues" })).toBeVisible();
  await page.goto(bdTechnical!.deep_link);
  await expect(page.getByText("OPENED FROM ISSUE", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ready for BD", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Confirm project & sources/i })).toHaveCount(0);
  await page.goto(bdCommercial!.deep_link);
  await expect(page.getByText("OPENED FROM ISSUE", { exact: true })).toBeVisible();
  await expect(page.getByText("Proposal Detail", { exact: false }).first()).toBeVisible();

  const engineeringIssues = await issuesFor(page, "ENGINEERING");
  const engineeringTechnical = engineeringIssues.find((item) => item.domain === "PROPOSAL_TECHNICAL");
  const permitTechnical = engineeringIssues.find((item) => item.domain === "PERMIT_TECHNICAL");
  const authority = engineeringIssues.find((item) => item.domain === "AUTHORITY");
  expect(engineeringTechnical?.actionability).toBe("ACTIONABLE");
  await page.goto("/issues");
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByRole("heading", { name: "Engineering issues" })).toBeVisible();
  await page.goto(engineeringTechnical!.deep_link);
  await expect(page.getByText("Proposal Preparation", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ready for BD", exact: true })).toBeVisible();
  await page.goto(permitTechnical!.deep_link);
  await expect(page.getByText("Verify the facts that drive the permit", { exact: true })).toBeVisible();
  await page.goto(authority!.deep_link);
  await expect(page.getByRole("heading", { name: "Comments & Corrections", exact: true })).toBeVisible();
});

test("focused Permit target rejects cross-project issue selection and remains usable on mobile", async ({ page }) => {
  await page.goto("/issues");
  const issues = await issuesFor(page, "OWNER");
  const permitIssue = issues.find((item) => item.domain === "PERMIT_TECHNICAL");
  const otherIssue = issues.find((item) => item.domain === "PROPOSAL_TECHNICAL");
  expect(permitIssue && otherIssue).toBeTruthy();
  const projectId = permitIssue!.deep_link.split("/")[2];
  const response = await page.request.get(`/api/projects/${projectId}?issue=${otherIssue!.id}`);
  expect(response.status()).toBe(409);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(permitIssue!.deep_link);
  await expect(page.getByText("OPENED FROM ISSUE", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
