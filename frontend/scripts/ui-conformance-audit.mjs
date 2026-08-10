import fs from "node:fs";
import path from "node:path";

const frontendRoot = process.cwd();
const repoRoot = path.resolve(frontendRoot, "..");
const sourceRoot = path.join(repoRoot, "artifacts", "universal-design-audit");
const auditRoot = path.join(repoRoot, "artifacts", "ui-conformance");

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const writeJson = (file, value) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
};

const sourceInventory = readJson(path.join(sourceRoot, "route-inventory.json"));
const sourceContracts = readJson(path.join(sourceRoot, "page-design-contracts.json"));
const sourceDefects = readJson(path.join(sourceRoot, "design-defects.json"));
const contractById = new Map(sourceContracts.contracts.map((contract) => [contract.id, contract]));
const commonForbidden = sourceContracts.common_forbidden_owner_terms || [];

const routeInventory = {
  audit_version: "proposalops-ui-conformance-v1",
  discovered_from: [
    "frontend/src/App.tsx",
    "frontend/src/ProductionReadiness.tsx",
    "frontend/src/AdministrationOwner.tsx",
    "frontend/src/ProposalsContracts.tsx",
    "frontend/src/AMECWork.tsx",
    "human-like browser navigation crawl"
  ],
  router_definition_route_count: sourceInventory.material_routes.length,
  material_routes: sourceInventory.material_routes.map((route) => ({
    ...route,
    discovered_by: ["router-definition", "direct-navigation-crawl"],
    applicable_viewports: ["desktop", "tablet", "mobile"],
    important_states: ["normal", "loading", "empty", "filter-empty", "error", "blocked", "read-only", "historical", "disabled-action"]
  })),
  route_count: sourceInventory.material_routes.length,
  route_discovery_status: "PENDING_BROWSER_EXECUTION",
  required_gate: "UI_ROUTE_DISCOVERY_GAP_ZERO"
};

const pageContracts = {
  audit_version: "proposalops-ui-conformance-v1",
  design_oracle: "ProposalOps / AMEC universal UI conformance brief",
  contracts: sourceInventory.material_routes.map((route) => {
    const source = contractById.get(route.contract_id);
    return {
      id: route.id,
      route: route.route,
      aliases: route.aliases || [],
      business_purpose: source?.purpose || `${route.domain} material screen`,
      domain: route.domain,
      allowed_personas: route.roles,
      expected_title: source?.heading || route.id,
      expected_record_identity: ["business reference", "record name", "related record context"],
      expected_stage_status: ["business lifecycle", "workflow stage", "blocking/readiness state"],
      expected_sections: source?.required || ["identity", "state", "next action", "evidence", "empty/loading/error handling"],
      expected_fields: source?.required || [],
      expected_actions: source?.actions || [],
      role_specific_controls: route.roles.map((persona) => ({ persona, classification: "CONTRACT_REQUIRED" })),
      expected_empty_state: "truthful empty or filtered-empty state",
      expected_loading_state: "loading state with page context",
      expected_error_state: "safe error state with retry and page context",
      expected_navigation: ["AMEC Work", "Proposals & Contracts", "Issues", "Notifications", "Operating Guide"],
      allowed_permit_terminology: route.domain === "downstream-permit" ? ["Permit", "Municipality", "Authority"] : ["downstream Permit handoff only"],
      forbidden_stale_terminology: ["PermitOps", "My Work", "About PermitOps", "Permit-first upstream framing"],
      forbidden_technical_terminology: commonForbidden
    };
  }),
  contract_count: sourceInventory.material_routes.length,
  coverage_rule: "Every material route, alias, persona, state, and viewport resolves to a contract."
};

const rolePageMatrix = {
  audit_version: "proposalops-ui-conformance-v1",
  personas: ["Owner", "Business Development", "Engineering"],
  combinations: sourceInventory.material_routes.flatMap((route) => route.roles.map((persona) => ({
    route_id: route.id,
    route: route.route,
    persona,
    internal_role: persona === "Owner" ? "SYSTEM_ADMIN" : persona === "Business Development" ? "COMMERCIAL_APPROVER" : "RESPONSIBLE_ENGINEER",
    view: "required",
    action_authority: "contract-required",
    desktop: "required",
    tablet: "required",
    mobile: "required"
  }))),
  combination_count: sourceInventory.material_routes.reduce((count, route) => count + route.roles.length, 0)
};

const defects = {
  audit_version: "proposalops-ui-conformance-v1",
  source_defects: sourceDefects.defects,
  new_gate_defects: [
    { id: "UCF-P1-001", route: "all material routes", persona: "all", severity: "P1", rule: "OWNER_FACING_CONCATENATED_TEXT_ZERO", status: "PENDING_BROWSER_EXECUTION", observed: "Needs runtime bounding-box and structural checks." },
    { id: "UCF-P1-002", route: "all material routes", persona: "all", severity: "P1", rule: "RAW_ENUM_VISIBLE_ZERO", status: "PENDING_BROWSER_EXECUTION", observed: "Needs runtime allowlist audit across all role/viewport combinations." },
    { id: "UCF-P1-003", route: "all material routes", persona: "all", severity: "P1", rule: "UI_CRAWL_NETWORK_FAILURE_ZERO", status: "PENDING_REAL_STACK_EXECUTION", observed: "Current focused tests use synthetic API mocks; real-stack network proof is still required." }
  ],
  p0_open: 0,
  p1_open: sourceDefects.defects.filter((defect) => defect.severity === "P1").length + 3,
  status: "NOT_READY_PENDING_GATE_EXECUTION"
};

const pending = (gate, note) => ({ gate, status: "PENDING_BROWSER_EXECUTION", note });
const textQuality = {
  audit_version: "proposalops-ui-conformance-v1",
  allowlist: ["QID", "NOC", "MFA", "RFQ", "RFP", "SOW", "API", "AMEC"],
  forbidden_runtime_patterns: ["raw UUID", "raw JSON", "snake_case", "SYSTEM_ADMIN", "COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER", "WorkflowTask", "WorkProjectionService", "PERSONA_FIXTURE"],
  results: [],
  ...pending("OWNER_FACING_TECHNICAL_TEXT_ZERO", "Generated by the exhaustive browser crawl.")
};
const statusSemantic = { ...pending("UI_STATUS_SEMANTIC_CLARITY_PASS", "Every visible status must be classified by dimension."), dimensions: ["business lifecycle", "workflow stage", "setup readiness", "integration health", "source relationship", "read state", "delivery state", "issue severity", "issue blocking state", "template state"], ambiguous_statuses: [] };
const kpiParity = { ...pending("UI_KPI_LIST_PARITY_PASS", "Each KPI/list pair requires fixture-backed reconciliation."), checks: [] };
const contradictions = { ...pending("PAGE_INTERNAL_CONTRADICTION_ZERO", "Page-specific semantic assertions run during the browser crawl."), findings: [] };
const crossPage = { ...pending("CROSS_PAGE_UI_TRUTH_PASS", "Register, detail, work, issues, notifications, and administration need shared-record comparison."), findings: [] };
const actionParity = { ...pending("UI_ROLE_ACTION_PARITY_PASS", "Each visible action must be classified and compared with backend authority."), classifications: [] };
const layout = { ...pending("UI_OVERLAP_COLLISION_ZERO", "DOM bounding boxes, horizontal overflow, blank sections, and duplication run during the browser crawl."), screenshots_directory: "artifacts/ui-conformance/screenshots", results: [] };
const mobile = { ...pending("UI_MOBILE_PASS", "Desktop, tablet, and mobile are rendered for every applicable persona."), viewports: { desktop: [1440, 1000], tablet: [834, 1112], mobile: [390, 844] }, results: [] };
const accessibility = { ...pending("UI_ACCESSIBILITY_PASS", "Axe and targeted keyboard/focus checks run during the browser crawl."), results: [] };
const networkConsole = { ...pending("UI_CRAWL_CONSOLE_ERROR_ZERO", "Network and console listeners run during the browser crawl."), console_errors: [], request_failures: [], bad_responses: [] };

writeJson(path.join(auditRoot, "route-inventory.json"), routeInventory);
writeJson(path.join(auditRoot, "page-ui-contracts.json"), pageContracts);
writeJson(path.join(auditRoot, "role-page-matrix.json"), rolePageMatrix);
writeJson(path.join(auditRoot, "ui-defects.json"), defects);
writeJson(path.join(auditRoot, "text-quality-results.json"), textQuality);
writeJson(path.join(auditRoot, "status-semantic-results.json"), statusSemantic);
writeJson(path.join(auditRoot, "kpi-list-parity.json"), kpiParity);
writeJson(path.join(auditRoot, "internal-contradictions.json"), contradictions);
writeJson(path.join(auditRoot, "cross-page-truth.json"), crossPage);
writeJson(path.join(auditRoot, "action-role-parity.json"), actionParity);
writeJson(path.join(auditRoot, "layout-results.json"), layout);
writeJson(path.join(auditRoot, "mobile-results.json"), mobile);
writeJson(path.join(auditRoot, "accessibility-results.json"), accessibility);
writeJson(path.join(auditRoot, "network-console-results.json"), networkConsole);
writeJson(path.join(auditRoot, "final-result.json"), {
  decision: "PROPOSALOPS_UI_CONFORMANCE_NOT_READY",
  generated_by: "frontend/scripts/ui-conformance-audit.mjs",
  material_route_count: routeInventory.route_count,
  contract_count: pageContracts.contract_count,
  role_page_combination_count: rolePageMatrix.combination_count,
  required_gates: [
    "UI_ROUTE_DISCOVERY_GAP_ZERO", "MATERIAL_UI_CONTRACT_COVERAGE_100_PERCENT", "OWNER_FACING_TECHNICAL_TEXT_ZERO", "OWNER_FACING_CONCATENATED_TEXT_ZERO", "RAW_ACTOR_CODE_VISIBLE_ZERO", "RAW_ENUM_VISIBLE_ZERO", "UI_INFORMATION_HIERARCHY_PASS", "CURRENT_VS_VIEWED_STAGE_UI_PASS", "UI_STATUS_SEMANTIC_CLARITY_PASS", "UI_ROLE_ACTION_PARITY_PASS", "AMBIGUOUS_UI_CTA_ZERO", "PAGE_INTERNAL_CONTRADICTION_ZERO", "CROSS_PAGE_UI_TRUTH_PASS", "UI_KPI_LIST_PARITY_PASS", "CONTRACT_DETAIL_UI_CONFORMANCE_PASS", "UI_OVERLAP_COLLISION_ZERO", "UNINTENDED_HORIZONTAL_OVERFLOW_ZERO", "BLANK_MAJOR_UI_SECTION_ZERO", "UNINTENTIONAL_UI_DUPLICATION_ZERO", "UI_FAKE_EMPTY_OR_HEALTH_ZERO", "UI_TERMINOLOGY_CONFORMANCE_PASS", "UI_SYNTHETIC_LABEL_CONSISTENCY_PASS", "UI_POST_MUTATION_REFRESH_CONSISTENCY_PASS", "UI_ACCESSIBILITY_PASS", "UI_MOBILE_PASS", "UI_CRAWL_CONSOLE_ERROR_ZERO", "UI_CRAWL_NETWORK_FAILURE_ZERO", "ROLE_UI_DIFFERENCE_INTENTIONAL_PASS", "PROPOSALOPS_UI_CONFORMANCE_READY"
  ],
  exact_gaps: [
    "The exhaustive browser crawl has not yet populated runtime evidence.",
    "Existing universal-design defects include P1 upstream framing, admin route classification, technical leakage, source status semantics, and legacy error-state handling.",
    "Real-stack network/console and screenshot semantic review remain required."
  ]
});

console.log(`Prepared ProposalOps UI conformance artifacts for ${routeInventory.route_count} material routes and ${rolePageMatrix.combination_count} route/persona combinations.`);
