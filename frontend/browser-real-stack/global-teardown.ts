export default async function globalTeardown() {
  const base = process.env.BASE_URL || "http://127.0.0.1:5173";
  try {
    const response = await fetch(`${base}/api/test-support/master-content/owner-cleanup`, { method: "POST", headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    if (!response.ok) throw new Error(`cleanup returned ${response.status}`);
    const result = await response.json();
    console.log(`owner_test_cleanup=PASS archived_master=${result.archived_master?.length || 0} archived_definitions=${result.archived_definitions?.length || 0}`);
  } catch (error) {
    console.error(`owner_test_cleanup=FAIL ${error instanceof Error ? error.message : String(error)}`);
    throw error;
  }
  try {
    const response = await fetch(`${base}/api/owner-decisions/test-support/cleanup`, { method: "POST", headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    if (!response.ok) throw new Error(`decision cleanup returned ${response.status}`);
    const result = await response.json();
    console.log(`owner_decision_test_cleanup=PASS reset=${result.decisions_reset || 0} history=${result.history_removed || 0}`);
  } catch (error) {
    console.error(`owner_decision_test_cleanup=FAIL ${error instanceof Error ? error.message : String(error)}`);
    throw error;
  }
}
