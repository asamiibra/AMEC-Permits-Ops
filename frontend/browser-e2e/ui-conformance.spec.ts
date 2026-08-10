import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";

type Persona = "Owner" | "Business Development" | "Engineering";
const internalRole: Record<Persona, string> = { Owner: "SYSTEM_ADMIN", "Business Development": "COMMERCIAL_APPROVER", Engineering: "RESPONSIBLE_ENGINEER" };
const viewports = { desktop: { width: 1440, height: 1000 }, tablet: { width: 834, height: 1112 }, mobile: { width: 390, height: 844 } };
const repoRoot = path.resolve(process.cwd(), "..");
const auditRoot = path.join(repoRoot, "artifacts", "ui-conformance");
const inventory = JSON.parse(fs.readFileSync(path.join(auditRoot, "route-inventory.json"), "utf8"));
const contracts = JSON.parse(fs.readFileSync(path.join(auditRoot, "page-ui-contracts.json"), "utf8"));
const contractById = new Map(contracts.contracts.map((item: any) => [item.id, item]));
const technicalAllowlist = new Set(["QID", "NOC", "MFA", "RFQ", "RFP", "SOW", "API", "AMEC", "SYN", "AI"]);
const rawActorPattern = /\b(?:SYSTEM_ADMIN|OWNER_SPONSOR|COMMERCIAL_APPROVER|RESPONSIBLE_ENGINEER|PERMIT_PREPARER|DEMO_AS_OPERATOR|PERSONA_FIXTURE)\b/;
const rawUuidPattern = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i;
const rawJsonPattern = /(?:\{\s*["']?[A-Za-z_]+["']?\s*:|\[\s*\{\s*["']?[A-Za-z_]+["']?\s*:)/;
const rawEnumPattern = /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g;

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };
const application = { id: "app-0142", project_id: project.id, external_request_number: "GHCE-APP-0142", application_status: "UNDER_REVIEW", repetition_count: 1, municipality: "Doha", permit_type: "Building Permit", last_status_at: "2026-08-08T12:00:00Z" };
const proposal = { id: "opp-1", proposal_id: "SYN-OPP-0001", proposal_description: "Al Noor Villa Proposal", project_reference: project.project_number, proposal_status: "PROPOSAL_PREPARATION", current_stage: "Engineering Proposal Preparation", reference_state: "CANONICAL", source_count: 1, amount: "QAR 100,000", related_contract_id: "contract-1", last_activity: "2026-08-08T12:00:00Z", next_action: { code: "VIEW_CONTRACT", label: "Review Proposal", eligible: true } };
const contract = { id: "contract-1", contract_reference: "SYN-CON-0001", related_proposal: proposal.proposal_description, related_proposal_id: proposal.id, project_reference: project.project_number, amount: "QAR 100,000", status: "ACTIVE", end_date: "2026-12-31", last_activity: "2026-08-08T12:00:00Z", permit_id: null, permit_eligible: true };

function proposalRegister(persona: string) {
  const owner = persona === "SYSTEM_ADMIN";
  const engineering = persona === "RESPONSIBLE_ENGINEER";
  return {
    persona: { allowed_actions: owner ? ["NEW_PROPOSAL", "CLIENT_LIST", "PROPOSAL_FORM", "CONTRACT_FORM"] : engineering ? ["PROPOSAL_FORM"] : ["NEW_PROPOSAL", "CLIENT_LIST", "PROPOSAL_FORM", "CONTRACT_FORM"], source_actions: owner || engineering ? ["TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION"] : ["TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION"], amount_visible: !engineering },
    rows: [proposal], contract_rows: [contract], clients: [{ id: "client-1", reference: "CLI-0001", name: "Al Noor Client", status: "ACTIVE" }], eligible_proposals: [proposal], eligible_contracts: [contract],
    kpis: { OPEN_PROPOSALS: { label: "Open Proposals", count: 1 }, OPEN_CONTRACTS: { label: "Open Contracts", count: 1 }, PROPOSAL_HANDOVER: { label: "Proposal Handover", count: 0 }, CONTRACT_HANDOVER: { label: "Contract Handover", count: 0 }, PROPOSALS_IN_PROCESS: { label: "Proposals in Process", count: 1 }, CONTRACTS_IN_PROCESS: { label: "Contracts in Process", count: 1 } },
    filters: [{ key: "ALL", label: "All" }, { key: "OPEN", label: "Open" }], filter_predicates: { proposal: { ALL: null, OPEN: ["PROPOSAL_PREPARATION"] }, contract: { ALL: null, OPEN: ["ACTIVE"] } }
  };
}

async function fulfillApi(route: any) {
  const url = new URL(route.request().url());
  const pathName = url.pathname;
  const persona = url.searchParams.get("persona") || "OWNER";
  let body: any = {};
  if (pathName === "/api/projects") body = [project];
  else if (pathName === "/api/applications") body = [application];
  else if (pathName === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
  else if (pathName === "/api/work") body = { summary: { needs_action: 1, waiting_review: 0, blocked: 1, overdue: 0 }, items: [{ id: "work-1", title: "Review Proposal", business_context: "Technical Proposal Preparation requires review.", domain: "proposal", reference: proposal.proposal_id, assigned_team: "Engineering", stage: "Engineering Proposal Preparation", cta_label: "Open Proposal", deep_link: `/proposals/${proposal.id}/preparation`, blocking: true }], unfiltered_visible_count: 1, context_visible_count: 1, recent_changes: [] };
  else if (pathName === "/api/proposals-main") body = proposalRegister(persona);
  else if (pathName === `/api/proposals-main/proposals/${proposal.id}`) body = { proposal, readiness: { client_context: true }, fields: { description: proposal.proposal_description, price: proposal.amount, period: "12 months", sow: "Design and engineering services", exclusions: "Not recorded", process_of_work: "Engineering review" }, sources: [{ id: "source-1", artifact_class: "TENDER_DOCUMENT", filename: "Tender brief.pdf", version: 1, verification_status: "READ_BACK_VERIFIED", current: true, sor_binding: "Project source" }], contracts: [contract], issues: [], tasks: [{ id: "handoff-1", title: "Engineering preparation", owner_role: "Engineering", status: "READY" }] };
  else if (pathName === `/api/proposals-main/contracts/${contract.id}`) body = { contract, project: { id: project.id, reference: project.project_number, name: project.project_name }, proposal: { id: proposal.id, reference: proposal.proposal_id, title: proposal.proposal_description, status: proposal.proposal_status }, revisions: [{ id: "revision-1", revision_number: 1, status: "CURRENT" }], permits: [], sources: [{ id: "source-2", artifact_class: "CONTRACT_FORM", verification_status: "READ_BACK_VERIFIED", path: "Contract source" }], issues: [], history: [{ id: "audit-1" }], next_action: { label: "Initiate Permit", eligible: true } };
  else if (pathName === "/api/issues" || pathName === "/api/issues/summary") body = pathName.endsWith("summary") ? { summary: { persona, open_issues: 0, blocking_issues: 0, work_items_affected: 0, overdue_unassigned: 0 } } : { persona, issues: [] };
  else if (pathName === "/api/notifications" || pathName === "/api/notifications/summary") body = pathName.endsWith("summary") ? { summary: { persona, unread: 0, proposal_updates: 0, handoffs: 0, permit_authority_updates: 0, contract_updates: 0 } } : { persona, notifications: [] };
  else if (pathName === "/api/notifications/observability") body = { delivery_failure_rate: 0, fallback_recipient_visible: false };
  else if (pathName === "/api/findings") body = { findings: [] };
  else if (pathName === "/api/tasks") body = { tasks: [] };
  else if (/\/api\/projects\/[^/]+\/documents$/.test(pathName)) body = [];
  else if (/\/api\/projects\/[^/]+\/conflicts$/.test(pathName)) body = [];
  else if (/\/api\/projects\/[^/]+\/readiness$/.test(pathName)) body = { evaluation: { overall_status: "READY" } };
  else if (/\/api\/projects\/[^/]+$/.test(pathName)) body = { office: { name_en: "AMEC Engineering" }, links: [{ id: "link-1", system_type: "SYNOLOGY", display_reference: "Project source" }, { id: "link-2", system_type: "EXCEL", display_reference: "Project tracker" }, { id: "link-3", system_type: "MUNICIPALITY", display_reference: application.external_request_number }], applications: [application], workflow: { stage: "VERIFY_DATA", next_action: { action_label: "Verify proposal data", action_code: "VERIFY_DATA", owner_role: "Engineering", stage: "VERIFY_DATA", blocking: false, reason: "Review source evidence." }, sources: [], confirmed_at: null }, audit: [] };
  else if (pathName.includes("monitoring-history")) body = { comments: [] };
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

function canonicalRoute(entry: any) {
  return entry.aliases?.find((alias: string) => alias.startsWith("/proposals-contracts")) || entry.route;
}

async function snapshot(page: any) {
  return page.evaluate(({ technicalAllowlist: allowed }) => {
    const main = document.querySelector("main") || document.body;
    const text = (main.innerText || "").replace(/\s+/g, " ").trim();
    const headings = [...main.querySelectorAll("h1,h2,h3")].map((node) => node.textContent?.replace(/\s+/g, " ").trim()).filter(Boolean);
    const candidates = [...main.querySelectorAll("[role=button],button,a,h1,h2,h3,dt,dd,.tag,.status")];
    const collisions: string[] = [];
    for (const parent of [...main.querySelectorAll("section,.panel,.page-intro,.detail-field,.detail-status-grid,.detail-status-strip")]) {
      const children = [...parent.children].filter((node) => (node.textContent || "").trim());
      for (let index = 0; index < children.length; index += 1) for (let next = index + 1; next < children.length; next += 1) {
        const a = children[index].getBoundingClientRect(); const b = children[next].getBoundingClientRect();
        if (a.width && b.width && a.height && b.height && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top && !children[index].contains(children[next]) && !children[next].contains(children[index])) collisions.push(`${children[index].textContent?.trim()} <> ${children[next].textContent?.trim()}`);
      }
    }
    const blankSections = [...main.querySelectorAll("section")].filter((section) => { const heading = section.querySelector("h1,h2,h3"); return heading && (section.innerText || "").trim().length <= (heading.textContent || "").trim().length + 8; }).map((section) => section.querySelector("h1,h2,h3")?.textContent?.trim());
    const technical = (text.match(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g) || []).filter((item) => !allowed.includes(item) && !item.startsWith("SYNTHETIC"));
    return { text, headings, title: document.title, current_stage_visible: /Current stage/i.test(text), viewed_stage_visible: /Viewing/i.test(text), raw_uuid: /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i.test(text), raw_json: /(?:\{\s*["']?[A-Za-z_]+["']?\s*:)/.test(text), raw_actor: /\b(?:SYSTEM_ADMIN|OWNER_SPONSOR|COMMERCIAL_APPROVER|RESPONSIBLE_ENGINEER|PERMIT_PREPARER|DEMO_AS_OPERATOR|PERSONA_FIXTURE)\b/.test(text), raw_enum: technical, blank_sections: blankSections, collisions, horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1, technical_allowlist: allowed };
  }, { technicalAllowlist: [...technicalAllowlist] });
}

test.describe("ProposalOps universal UI conformance gate", () => {
  test.setTimeout(300_000);

  test("crawls every material route, persona, and viewport and writes conformance evidence", async ({ page }) => {
    fs.mkdirSync(path.join(auditRoot, "screenshots"), { recursive: true });
    await page.route("**/api/**", fulfillApi);
    const results: any[] = [];
    const consoleErrors: string[] = [];
    const requestFailures: string[] = [];
    const badResponses: string[] = [];
    page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
    page.on("requestfailed", (request) => requestFailures.push(`${request.method()} ${request.url()}`));
    page.on("response", (response) => { if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`); });

    for (const persona of ["Owner", "Business Development", "Engineering"] as Persona[]) {
      await page.goto("/work");
      await page.evaluate((role) => sessionStorage.setItem("proposalops-role", role), internalRole[persona]);
      for (const entry of inventory.material_routes) {
        if (!entry.roles.includes(persona)) continue;
        const route = canonicalRoute(entry);
        for (const [viewport, size] of Object.entries(viewports)) {
          await page.setViewportSize(size);
          await page.goto(route, { waitUntil: "domcontentloaded" });
          await page.waitForTimeout(80);
          const current = await snapshot(page);
          const axe = viewport === "desktop" && ["S01", "S02", "S02A", "S02B", "S02C", "S02D", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12", "S13", "S14", "S15", "S26"].includes(entry.id) ? await new AxeBuilder({ page }).analyze() : { violations: [] };
          const screenshot = path.join(auditRoot, "screenshots", `${entry.id}-${persona.replaceAll(" ", "-")}-${viewport}.png`);
          await page.screenshot({ path: screenshot, fullPage: true });
          results.push({ route_id: entry.id, route, persona, viewport, contract: contractById.has(entry.id), ...current, axe_critical_or_serious: axe.violations.filter((item) => ["critical", "serious"].includes(item.impact || "")).map((item) => item.id), screenshot: path.relative(repoRoot, screenshot) });
        }
      }
    }

    const checks = {
      UI_ROUTE_DISCOVERY_GAP_ZERO: inventory.route_count === inventory.material_routes.length && results.length > 0,
      MATERIAL_UI_CONTRACT_COVERAGE_100_PERCENT: results.every((item) => item.contract),
      OWNER_FACING_TECHNICAL_TEXT_ZERO: results.every((item) => !item.raw_uuid && !item.raw_json && !item.raw_actor && item.raw_enum.length === 0),
      OWNER_FACING_CONCATENATED_TEXT_ZERO: results.every((item) => item.collisions.length === 0),
      RAW_ACTOR_CODE_VISIBLE_ZERO: results.every((item) => !item.raw_actor),
      RAW_ENUM_VISIBLE_ZERO: results.every((item) => item.raw_enum.length === 0),
      CURRENT_VS_VIEWED_STAGE_UI_PASS: results.filter((item) => item.route.includes("project-and-sources") || item.route.includes("verify-data") || item.route.includes("prepare-package") || item.route.includes("municipality-preparation") || item.route.includes("final-review") || item.route.includes("authority-review") || item.route.includes("comments-and-corrections") || item.route.includes("history")).every((item) => item.current_stage_visible && item.viewed_stage_visible),
      UI_OVERLAP_COLLISION_ZERO: results.every((item) => item.collisions.length === 0),
      UNINTENDED_HORIZONTAL_OVERFLOW_ZERO: results.every((item) => !item.horizontal_overflow),
      BLANK_MAJOR_UI_SECTION_ZERO: results.every((item) => item.blank_sections.length === 0),
      UI_ACCESSIBILITY_PASS: results.every((item) => item.axe_critical_or_serious.length === 0),
      UI_CRAWL_CONSOLE_ERROR_ZERO: consoleErrors.length === 0,
      UI_CRAWL_NETWORK_FAILURE_ZERO: requestFailures.length === 0 && badResponses.length === 0,
      ROLE_UI_DIFFERENCE_INTENTIONAL_PASS: false,
      UI_STATUS_SEMANTIC_CLARITY_PASS: false,
      UI_ROLE_ACTION_PARITY_PASS: false,
      PAGE_INTERNAL_CONTRADICTION_ZERO: false,
      CROSS_PAGE_UI_TRUTH_PASS: false,
      UI_KPI_LIST_PARITY_PASS: false,
      CONTRACT_DETAIL_UI_CONFORMANCE_PASS: false,
      UI_FAKE_EMPTY_OR_HEALTH_ZERO: false,
      UI_TERMINOLOGY_CONFORMANCE_PASS: false,
      UI_SYNTHETIC_LABEL_CONSISTENCY_PASS: false,
      UI_POST_MUTATION_REFRESH_CONSISTENCY_PASS: false,
      UI_MOBILE_PASS: results.filter((item) => item.viewport === "mobile").every((item) => !item.horizontal_overflow),
      AMBIGUOUS_UI_CTA_ZERO: false,
      UI_INFORMATION_HIERARCHY_PASS: false,
      UNINTENTIONAL_UI_DUPLICATION_ZERO: false
    };
    const ready = Object.values(checks).every(Boolean);
    fs.writeFileSync(path.join(auditRoot, "runtime-results.json"), JSON.stringify({ generated_at: new Date().toISOString(), route_count: inventory.route_count, result_count: results.length, results, console_errors: consoleErrors, request_failures: requestFailures, bad_responses: badResponses, checks }, null, 2) + "\n");
    fs.writeFileSync(path.join(auditRoot, "text-quality-results.json"), JSON.stringify({ gate: "OWNER_FACING_TECHNICAL_TEXT_ZERO", status: checks.OWNER_FACING_TECHNICAL_TEXT_ZERO ? "PASS" : "FAIL", result_count: results.length, failures: results.filter((item) => item.raw_uuid || item.raw_json || item.raw_actor || item.raw_enum.length).slice(0, 100) }, null, 2) + "\n");
    fs.writeFileSync(path.join(auditRoot, "layout-results.json"), JSON.stringify({ gates: { UI_OVERLAP_COLLISION_ZERO: checks.UI_OVERLAP_COLLISION_ZERO, UNINTENDED_HORIZONTAL_OVERFLOW_ZERO: checks.UNINTENDED_HORIZONTAL_OVERFLOW_ZERO, BLANK_MAJOR_UI_SECTION_ZERO: checks.BLANK_MAJOR_UI_SECTION_ZERO }, result_count: results.length, failures: results.filter((item) => item.collisions.length || item.horizontal_overflow || item.blank_sections.length).slice(0, 100) }, null, 2) + "\n");
    fs.writeFileSync(path.join(auditRoot, "mobile-results.json"), JSON.stringify({ gate: "UI_MOBILE_PASS", status: checks.UI_MOBILE_PASS ? "PASS" : "FAIL", viewports, failures: results.filter((item) => item.viewport === "mobile" && item.horizontal_overflow) }, null, 2) + "\n");
    fs.writeFileSync(path.join(auditRoot, "accessibility-results.json"), JSON.stringify({ gate: "UI_ACCESSIBILITY_PASS", status: checks.UI_ACCESSIBILITY_PASS ? "PASS" : "FAIL", failures: results.filter((item) => item.axe_critical_or_serious.length).slice(0, 100) }, null, 2) + "\n");
    fs.writeFileSync(path.join(auditRoot, "network-console-results.json"), JSON.stringify({ gates: { UI_CRAWL_CONSOLE_ERROR_ZERO: checks.UI_CRAWL_CONSOLE_ERROR_ZERO, UI_CRAWL_NETWORK_FAILURE_ZERO: checks.UI_CRAWL_NETWORK_FAILURE_ZERO }, console_errors: consoleErrors, request_failures: requestFailures, bad_responses: badResponses }, null, 2) + "\n");
    const final = { decision: ready ? "PROPOSALOPS_UI_CONFORMANCE_READY" : "PROPOSALOPS_UI_CONFORMANCE_NOT_READY", checks, route_count: inventory.route_count, result_count: results.length, exact_gaps: Object.entries(checks).filter(([, value]) => !value).map(([key]) => key) };
    fs.writeFileSync(path.join(auditRoot, "final-result.json"), JSON.stringify(final, null, 2) + "\n");
    expect(results).toHaveLength(inventory.material_routes.reduce((total: number, entry: any) => total + entry.roles.length * Object.keys(viewports).length, 0));
  });

  test("enforces the final conformance decision", async () => {
    const final = JSON.parse(fs.readFileSync(path.join(auditRoot, "final-result.json"), "utf8"));
    expect(final.decision, JSON.stringify(final, null, 2)).toBe("PROPOSALOPS_UI_CONFORMANCE_READY");
  });
});
