import { test, expect } from "@playwright/test";

const projects = [
  { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" },
  { id: "p-0187", project_number: "GHCE-2026-0187", project_name: "West Bay Residence", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Rana Faisal" },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url()); const path = url.pathname;
    let body: any = {};
    if (path === "/api/projects") body = projects;
    else if (path === "/api/applications") body = [{ id: "a-0142", project_id: "p-0142", external_request_number: "GHCE-APP-0142", application_status: "UNDER_REVIEW", repetition_count: 1, municipality: "Doha", permit_type: "Building Permit", last_status_at: "2026-08-08T12:00:00Z" }, { id: "a-0187", project_id: "p-0187", external_request_number: "GHCE-APP-0187", application_status: "RETURNED", repetition_count: 2, municipality: "Doha", permit_type: "Building Permit", last_status_at: "2026-08-08T12:00:00Z" }];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === "/api/findings") body = { findings: [{ id: "f-0187", project_id: "p-0187", title: "Drawing revision requires review", raw_text: "Synthetic authority comment", source_type: "OFFICIAL_MUNICIPALITY_COMMENT", blocking: true, status: "OPEN", assignee_role: "Responsible Engineer" }] };
    else if (path === "/api/tasks") body = { tasks: [{ id: "t-0187", title: "Review returned drawing", owner_role: "Responsible Engineer", status: "ASSIGNED", finding: { project_id: "p-0187" } }] };
    else if (path === "/api/notifications") body = { notifications: [{ id: "n-0187", subject: "Returned application", event_type: "AUTHORITY_RETURNED", channel: "EMAIL", status: "FAILED", finding_id: "f-0187" }] };
    else if (path === "/api/notifications/observability") body = { delivery_failure_rate: 1, fallback_recipient_visible: true };
    else if (/\/api\/projects\/[^/]+$/.test(path)) body = { links: [{ id: "link-1", system_type: "SYNOLOGY", display_reference: "/synthetic/projects/GHCE-2026-0187" }, { id: "link-2", system_type: "EXCEL", display_reference: "Tracker / row 18" }, { id: "link-3", system_type: "MUNICIPALITY", display_reference: "GHCE-APP-0187" }], audit: [{ id: "audit-1", event_type: "PROJECT_BOOTSTRAPPED", occurred_at: "2026-08-08T12:00:00Z", entity_type: "Project", correlation_id: "corr-1" }] };
    else if (path.endsWith("/documents")) body = [{ id: "doc-1", document_type: "TITLE_DEED", current_version_id: "ver-1" }, { id: "doc-2", document_type: "DRAWING_SET", current_version_id: "ver-2" }];
    else if (path.endsWith("/conflicts")) body = [];
    else if (path.includes("monitoring-history")) body = { comments: [{ id: "comment-1" }] };
    await route.fulfill({ json: body });
  });
});

test("workflow-first operator can resume a returned permit through the permit workspace", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "West Bay Residence" }).first()).toBeVisible();
  await expect(page.locator(".workflow-section")).toContainText(/blocking|authority comments/i);
  await expect(page.getByRole("navigation").getByRole("button", { name: "Administration" })).toHaveCount(0);

  await page.getByRole("navigation").getByRole("button", { name: /Permits/ }).click();
  await page.getByRole("button", { name: "Open workspace" }).nth(1).click();
  await expect(page).toHaveURL(/\/permits\/p-0187\/comments-and-corrections$/);
  await expect(page.getByText("YOU ARE HERE")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Comments & Corrections" })).toBeVisible();

  for (const [label, path, heading] of [["Sources", "project-and-sources", "Establish the permit workspace"], ["Verify", "verify-data", "Verify the facts that drive the permit"], ["Package", "prepare-package", "Prepare Package"], ["Municipality", "municipality-preparation", "Municipality Preparation"], ["Final review", "final-review", "Ready for a named human decision"], ["Authority", "authority-review", "Application returned"], ["Corrections", "comments-and-corrections", "Comments & Corrections"], ["History", "history", "Permit evidence timeline"]] as const) {
    await page.getByRole("button", { name: new RegExp(label) }).click();
    await expect(page).toHaveURL(new RegExp(`/permits/p-0187/${path}$`));
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    if (label === "Sources") await expect(page.getByRole("main").getByText("AMEC Engineering", { exact: true })).toBeVisible();
    if (label === "Final review") await expect(page.getByText("NO MACHINE SUBMIT")).toBeVisible();
  }
});

test("privileged role exposes Administration without changing the business shell", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Role").selectOption("SYSTEM_ADMIN");
  await expect(page.getByRole("navigation").getByRole("button", { name: "Administration" })).toBeVisible();
  await page.getByRole("navigation").getByRole("button", { name: "Administration" }).click();
  await expect(page.getByRole("heading", { name: "Setup and system controls" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Project setup" })).toBeVisible();
});
