import { test, expect } from "@playwright/test";

const projects = [
  { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" },
  { id: "p-0187", project_number: "GHCE-2026-0187", project_name: "West Bay Residence", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Rana Faisal" },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/projects", route => route.fulfill({ json: projects }));
  await page.route("**/api/applications", route => route.fulfill({ json: projects.map((p, i) => ({ id: `a-${i}`, project_id: p.id, external_request_number: `GHCE-APP-${i ? "0187" : "0142"}`, application_status: i ? "RETURNED" : "DRAFT", repetition_count: i, municipality: p.municipality, permit_type: p.permit_type })) }));
  await page.route("**/api/reconciliation/governance", route => route.fulfill({ json: { environment_badge: "SYNTHETIC PROTOTYPE" } }));
  await page.route("**/api/proposals-main?**", route => route.fulfill({ json: { persona: { allowed_actions: [], source_actions: [], amount_visible: true }, rows: [], contract_rows: [], kpis: { OPEN_PROPOSALS: { label: "Open Proposals", count: 0 }, OPEN_CONTRACTS: { label: "Open Contracts", count: 0 }, PROPOSAL_HANDOVER: { label: "Proposal handover", count: 0 }, CONTRACT_HANDOVER: { label: "Contract handover", count: 0 }, PROPOSALS_IN_PROCESS: { label: "Proposals in process", count: 0 }, CONTRACTS_IN_PROCESS: { label: "Contracts in process", count: 0 } }, filters: [{ key: "ALL", label: "All" }], filter_predicates: { proposal: { ALL: null }, contract: { ALL: null } }, clients: [] } }));
});

test("canonical project bootstrap and safety controls", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".env-chip").getByText("SYNTHETIC PROTOTYPE", { exact: true })).toBeVisible();
  await expect(page.getByText("AMEC Engineering", { exact: true })).toBeVisible();
  await expect(page.getByText("Simulated integrations").first()).toBeVisible();
  await page.getByRole("navigation").getByRole("button", { name: "Proposals & Contracts" }).click();
  await expect(page.getByRole("heading", { name: "Proposals & Contracts", level: 2 })).toBeVisible();
  await expect(page.getByText("One governed commercial register from source intake to Proposal, Contract, and downstream Permit handoff.")).toBeVisible();
});
