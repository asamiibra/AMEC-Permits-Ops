import { expect, test } from "@playwright/test";

/**
 * Lightweight release harness for the current owner-facing route contracts.
 * Domain-specific suites remain responsible for mutation and authorization;
 * this harness prevents a material route from silently becoming a blank or
 * browser-error surface.
 */
test("current material routes render without browser or network errors", async ({ page, request }) => {
  const projects = await (await request.get("/api/projects")).json();
  const projectId = projects[0]?.id;
  const proposals = await (await request.get("/api/proposals-main?persona=SYSTEM_ADMIN")).json();
  const proposalId = proposals.proposals?.[0]?.id;
  const contracts = proposals.contracts || [];
  const contractId = contracts[0]?.id;
  const issues = await (await request.get("/api/issues?persona=OWNER")).json();
  const issueId = issues.issues?.[0]?.id;
  const routes = [
    "/work", "/proposals-contracts", "/proposals/new", "/issues", "/notifications", "/operating-guide",
    "/admin", "/admin/go-live-readiness", "/admin/people-access", "/admin/data-connections",
    "/admin/project-folder-setup", "/admin/proposal-setup", "/admin/contract-setup", "/admin/permit-setup",
    "/admin/templates", "/admin/notifications", "/admin/security", "/admin/integration-health", "/admin/audit",
    "/admin/advanced-diagnostics", "/admin/control-diagnostics", "/opportunities", "/engineering-closeout",
    ...(proposalId ? [`/proposals/${proposalId}`, `/proposals/${proposalId}/preparation`] : []),
    ...(contractId ? [`/contracts/${contractId}`] : []),
    ...(issueId ? [`/issues/${issueId}`] : []),
    ...(projectId ? [
      `/proposals-contracts/${projectId}/project-and-sources`, `/proposals-contracts/${projectId}/verify-data`,
      `/proposals-contracts/${projectId}/prepare-package`, `/proposals-contracts/${projectId}/municipality-preparation`,
      `/proposals-contracts/${projectId}/final-review`, `/proposals-contracts/${projectId}/authority-review`,
      `/proposals-contracts/${projectId}/comments-and-corrections`, `/proposals-contracts/${projectId}/history`,
    ] : []),
  ];
  const consoleErrors: string[] = [];
  const networkErrors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(`${message.text()} @ ${page.url()}`); });
  page.on("requestfailed", (requestEvent) => networkErrors.push(`${requestEvent.method()} ${requestEvent.url()} ${requestEvent.failure()?.errorText || "failed"}`));
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) networkErrors.push(`${response.request().method()} ${response.url()} HTTP ${response.status()}`); });
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator(".main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Something went wrong");
  }
  expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  expect(networkErrors, networkErrors.join("\n")).toEqual([]);
  expect(routes.length).toBeGreaterThanOrEqual(30);
});
