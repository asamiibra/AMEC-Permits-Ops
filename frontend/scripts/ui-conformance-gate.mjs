const CLOSED_STATUSES = new Set(["PASS", "PASS_RUNTIME", "CLOSED", "RESOLVED", "SUPERSEDED", "NOT_APPLICABLE", "N/A"]);
const DEFERRED_STATUSES = new Set(["DEFERRED", "DEFERRED_WITH_REASON"]);
const VALID_SCOPES = new Set(["UNIVERSAL", "MODULE_SPECIFIC", "SOURCE_REQUIRED", "NOT_APPLICABLE_WITH_REASON"]);
const VALID_SEVERITIES = new Set(["P0", "P1", "P2"]);

const rowsFrom = (defects = {}) => [...(defects.source_defects || []), ...(defects.new_gate_defects || []), ...(defects.defects || [])];
const isOpen = (row) => {
  const status = String(row.status || "OPEN").toUpperCase();
  return !CLOSED_STATUSES.has(status) && !(DEFERRED_STATUSES.has(status) && row.deferred_reason);
};

export function evaluateUiConformance({ defects = {}, runtimeChecks = {} } = {}) {
  const allRows = rowsFrom(defects);
  const unclassified = allRows.filter((row) => !VALID_SCOPES.has(String(row.scope || "")) || !VALID_SEVERITIES.has(String(row.severity || "")));
  const universalRows = allRows.filter((row) => row.scope === "UNIVERSAL" || !row.scope || !row.severity);
  const openUniversal = universalRows.filter(isOpen);
  const openBySeverity = (severity) => openUniversal.filter((row) => row.severity === severity).length;
  const unexplainedDeferred = openUniversal.filter((row) => DEFERRED_STATUSES.has(String(row.status || "").toUpperCase()) && !row.deferred_reason).length;
  const requiredUiTestsPass = Object.keys(runtimeChecks).length > 0 && Object.values(runtimeChecks).every(Boolean);
  const checks = {
    UNIVERSAL_P0_OPEN_ZERO: openBySeverity("P0") === 0,
    UNIVERSAL_P1_OPEN_ZERO: openBySeverity("P1") === 0,
    UNIVERSAL_P2_OPEN_ZERO: openBySeverity("P2") === 0,
    UNIVERSAL_UNCLASSIFIED_OPEN_ZERO: unclassified.filter(isOpen).length === 0,
    UNIVERSAL_UNEXPLAINED_DEFERRED_ZERO: unexplainedDeferred === 0,
    REQUIRED_UI_TESTS_PASS: requiredUiTestsPass,
    ACCESSIBILITY_CONFORMANCE_PASS: runtimeChecks.UI_ACCESSIBILITY_PASS === true,
    RESPONSIVE_CONFORMANCE_PASS: runtimeChecks.UI_MOBILE_PASS === true && runtimeChecks.UNINTENDED_HORIZONTAL_OVERFLOW_ZERO === true,
  };
  const ready = Object.values(checks).every(Boolean);
  return {
    decision: ready ? "PROPOSALOPS_UI_CONFORMANCE_READY" : "PROPOSALOPS_UI_CONFORMANCE_NOT_READY",
    ready,
    checks,
    defect_summary: {
      total: allRows.length,
      universal_total: universalRows.length,
      universal_p0_open: openBySeverity("P0"),
      universal_p1_open: openBySeverity("P1"),
      universal_p2_open: openBySeverity("P2"),
      universal_unclassified_open: unclassified.filter(isOpen).length,
      universal_unexplained_deferred: unexplainedDeferred,
      blocking_ids: openUniversal.filter(isOpen).map((row) => row.id || "UNIDENTIFIED"),
    },
  };
}
