import { test, expect } from "@playwright/test";

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };
const issue = { id: "issue-1", title: "Proposal SOW needs engineering confirmation", summary: "Engineering evidence is required before commercial review.", domain: "PROPOSAL_TECHNICAL", severity: "BLOCKING", blocking: true, status: "OPEN", owner_persona: "ENGINEERING", actionability: "ACTIONABLE", affected_record: { label: "SYN-OPP-0001" }, deep_link: "/proposals/opp-1/preparation?issue=issue-1", issue_detail_link: "/proposals/opp-1/preparation?issue=issue-1", cta_label: "Open Preparation" };
const event = { id: "event-1", subject: "Proposal preparation ready", message: "SYN-OPP-0001 is ready for commercial review.", event_type: "ENGINEERING_PROPOSAL_READY", domain: "PROPOSAL_TECHNICAL", severity: "ADVISORY", unread: true, actor: "Engineering", delivery_status: "DELIVERED", affected_record: { label: "SYN-OPP-0001" }, deep_link: "/proposals/opp-1/preparation", source_event_id: "event-1" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url()); const path = url.pathname; const persona = url.searchParams.get("persona") || "OWNER";
    let body: any = {};
    if (path === "/api/projects") body = [project];
    else if (path === "/api/applications") body = [{ id: "app-1", project_id: project.id, external_request_number: "GHCE-APP-0142", application_status: "DRAFT", repetition_count: 0 }];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === "/api/issues/summary") body = { summary: { persona, open_issues: 1, blocking_issues: 1, work_items_affected: 1, overdue_unassigned: 0 } };
    else if (path === "/api/issues") body = { persona, issues: [issue] };
    else if (path === "/api/notifications/summary") body = { summary: { persona, unread: 1, proposal_updates: 1, handoffs: 1, permit_authority_updates: 0, contract_updates: 1, client_handoff_updates: 1, commercial_updates: 1, engineering_permit_updates: 1, critical_alerts: 0 } };
    else if (path === "/api/notifications") body = { persona, notifications: [event] };
    else if (path === "/api/notifications/observability") body = { delivery_failure_rate: 0, fallback_recipient_visible: false };
    await route.fulfill({ json: body });
  });
});

test("persona switch changes issue copy, filters, and deep links", async ({ page }) => {
  await page.goto("/issues");
  await expect(page.getByRole("heading", { name: "Issues across AMEC work" })).toBeVisible();
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByRole("heading", { name: "Engineering issues" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Preparation" })).toHaveAttribute("href", "/proposals/opp-1/preparation?issue=issue-1&return_filter=ALL");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByRole("heading", { name: "Commercial & project issues" })).toBeVisible();
});

test("notifications keep persona KPIs separate from delivery diagnostics", async ({ page }) => {
  await page.goto("/notifications");
  await expect(page.getByRole("heading", { name: "Owner notifications", level: 2 })).toBeVisible();
  await expect(page.getByText("Proposal preparation ready")).toBeVisible();
  await expect(page.getByText("No delivery failures")).toBeVisible();
  await expect(page.getByRole("link", { name: "View event" })).toHaveAttribute("href", "/proposals/opp-1/preparation?notification=event-1&return_filter=ALL");
});

test("persona surfaces remain keyboard-addressable and responsive", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/issues");
  await expect(page.getByLabel("Persona")).toBeVisible();
  await expect(page.getByRole("button", { name: "All" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
