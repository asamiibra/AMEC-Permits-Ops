import { test, expect } from "@playwright/test";

const opportunity = { id: "opp-e3-1", opportunity_reference: "AMEC-OPP-0001", client_account_id: "client-e3-1", title: "Synthetic Building Advisory Opportunity", status: "CLIENT_RESPONSE_PENDING", current_owner_user_id: "bd-user" };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: any = {};
    if (path === "/api/projects") body = [];
    else if (path === "/api/applications") body = [];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === "/api/opportunities") body = [opportunity];
    else if (path === `/api/opportunities/${opportunity.id}`) body = { opportunity, rfqs: [{ id: "rfq-1", source_reference: "SYN-RFQ-001", status: "RECEIVED" }], tenders: [{ id: "tender-1", document_role: "TENDER", status: "RECEIVED" }], quotations: [{ quotation_reference: "SYN-QTN-001", status: "RELEASED_TO_CLIENT" }], responses: [{ response_type: "PENDING" }] };
    await route.fulfill({ json: body });
  });
});

test("E3/E4 Opportunities navigation is visible to authorized role", async ({ page }) => { await page.goto("/opportunities"); await expect(page.getByRole("navigation").getByRole("button", { name: "Opportunities" })).toBeVisible(); });
test("E3/E4 opportunity table shows reference and status", async ({ page }) => { await page.goto("/opportunities"); await expect(page.getByText("AMEC-OPP-0001")).toBeVisible(); await expect(page.getByText("CLIENT_RESPONSE_PENDING")).toBeVisible(); });
test("Opportunity workspace opens from the table", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByRole("heading", { name: "Synthetic Building Advisory Opportunity" })).toBeVisible(); });
test("Workspace shows RFQ and Sources step", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("RFQ & Sources", { exact: true })).toBeVisible(); await expect(page.getByText("SYN-RFQ-001")).toBeVisible(); });
test("Workspace shows tender evidence", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("Tender document")).toBeVisible(); await expect(page.getByText("EVIDENCE").first()).toBeVisible(); });
test("Quotation panel exposes release state", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByRole("heading", { name: "Quotation" })).toBeVisible(); await expect(page.getByText("SYN-QTN-001")).toBeVisible(); });
test("Quotation panel distinguishes non-binding values", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("AI / extracted values are not binding")).toBeVisible(); });
test("Commercial review names human authority", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByRole("heading", { name: "Commercial Review" })).toBeVisible(); await expect(page.getByText("COMMERCIAL_APPROVER")).toBeVisible(); });
test("Commercial review blocks autonomous release", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("NO AUTONOMOUS RELEASE")).toBeVisible(); });
test("Client response panel is revision-gated", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByRole("heading", { name: "Client Response" })).toBeVisible(); await expect(page.getByText("exact released quotation revision")).toBeVisible(); });
test("Contract and Setup is downstream of acceptance", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByRole("heading", { name: "Contract & Setup" })).toBeVisible(); await expect(page.getByText("GATED")).toBeVisible(); });
test("Workspace keeps human-send boundary visible", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("HUMAN SEND REQUIRED")).toBeVisible(); });
test("Workspace identifies the owner", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await expect(page.getByText("Owner: bd-user")).toBeVisible(); });
test("Workspace returns to Opportunities", async ({ page }) => { await page.goto("/opportunities"); await page.getByText("AMEC-OPP-0001").click(); await page.getByRole("button", { name: "Opportunities" }).first().click(); await expect(page.getByText("AMEC-OPP-0001")).toBeVisible(); });
