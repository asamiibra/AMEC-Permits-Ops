import { describe, expect, it } from "vitest";
import { evaluateUiConformance } from "../scripts/ui-conformance-gate.mjs";

const passingRuntime = { UI_ACCESSIBILITY_PASS: true, UI_MOBILE_PASS: true, UNINTENDED_HORIZONTAL_OVERFLOW_ZERO: true, UI_ROUTE_DISCOVERY_GAP_ZERO: true };
const row = (overrides = {}) => ({ id: "UCF-TEST", scope: "UNIVERSAL", severity: "P2", status: "CLOSED", ...overrides });

describe("ProposalOps UI conformance gate", () => {
  it.each([["P0", { severity: "P0" }], ["P1", { severity: "P1" }], ["P2", { severity: "P2" }]])("blocks an open universal %s", (_severity, overrides) => {
    const result = evaluateUiConformance({ defects: { defects: [row({ ...overrides, status: "OPEN" })] }, runtimeChecks: passingRuntime });
    expect(result.ready).toBe(false);
    expect(result.defect_summary.blocking_ids).toContain("UCF-TEST");
  });
  it("blocks an open unclassified universal defect", () => {
    const result = evaluateUiConformance({ defects: { defects: [row({ scope: undefined, status: "OPEN" })] }, runtimeChecks: passingRuntime });
    expect(result.ready).toBe(false);
    expect(result.defect_summary.universal_unclassified_open).toBe(1);
  });
  it("allows only closed or valid N/A rows when runtime tests pass", () => {
    const result = evaluateUiConformance({ defects: { defects: [row(), row({ id: "UCF-NA", scope: "NOT_APPLICABLE_WITH_REASON", status: "NOT_APPLICABLE", reason: "Not rendered by the universal shell." })] }, runtimeChecks: passingRuntime });
    expect(result.ready).toBe(true);
  });
  it("does not let a module-specific defect falsify universal conformance", () => {
    const result = evaluateUiConformance({ defects: { defects: [row({ scope: "MODULE_SPECIFIC", status: "OPEN" })] }, runtimeChecks: passingRuntime });
    expect(result.ready).toBe(true);
    expect(result.defect_summary.universal_p2_open).toBe(0);
  });
  it("rejects a manual READY flag while an applicable universal defect is open", () => {
    const result = evaluateUiConformance({ defects: { defects: [row({ status: "OPEN" })] }, runtimeChecks: passingRuntime, manualDecision: "READY" });
    expect(result.ready).toBe(false);
    expect(result.decision).toBe("PROPOSALOPS_UI_CONFORMANCE_NOT_READY");
  });
  it("requires runtime, accessibility, and responsive evidence", () => {
    expect(evaluateUiConformance({ defects: { defects: [] }, runtimeChecks: {} }).ready).toBe(false);
    expect(evaluateUiConformance({ defects: { defects: [] }, runtimeChecks: { ...passingRuntime, UI_ACCESSIBILITY_PASS: false } }).ready).toBe(false);
    expect(evaluateUiConformance({ defects: { defects: [] }, runtimeChecks: { ...passingRuntime, UI_MOBILE_PASS: false } }).ready).toBe(false);
  });
});
