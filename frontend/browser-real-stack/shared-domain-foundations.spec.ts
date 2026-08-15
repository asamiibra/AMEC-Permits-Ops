import { expect, test } from "@playwright/test";

test("real stack exposes the shared-foundation contracts on Postgres", async ({ request }) => {
  const suffix = Math.random().toString(16).slice(2, 10);
  const owner = { "X-Dev-Role": "SYSTEM_ADMIN" };

  const health = await request.get("/health");
  expect(health.ok()).toBeTruthy();
  const healthBody = await health.json();
  expect(healthBody.database_dialect).toBe("postgresql");
  expect(healthBody.alembic_versions).toContain("0055_bd_proposal_final_hardening");

  for (const path of [
    "/api/regulatory/external-bodies",
    "/api/requirements/definitions",
    "/api/technical-rules/sets",
    "/api/form-automation/profiles",
    "/api/shared-domain/future-seam",
  ]) {
    expect((await request.get(path, { headers: owner })).ok(), path).toBeTruthy();
  }

  const jurisdictionResponse = await request.post("/api/regulatory/jurisdictions", {
    headers: owner,
    data: { code: `BROWSER-J-${suffix}`, country_code: "ZZ", name_en: "Synthetic Browser Locality", level: "LOCALITY" },
  });
  expect(jurisdictionResponse.ok()).toBeTruthy();
  const jurisdiction = await jurisdictionResponse.json();

  const bodyResponse = await request.post("/api/regulatory/external-bodies", {
    headers: owner,
    data: { code: `BROWSER-B-${suffix}`, name_en: "Synthetic Browser Authority", body_type: "AUTHORITY", jurisdiction_id: jurisdiction.id, verification_state: "SYNTHETIC_UNVERIFIED" },
  });
  expect(bodyResponse.ok()).toBeTruthy();

  const definitionResponse = await request.post("/api/requirements/definitions", {
    headers: owner,
    data: { code: `BROWSER-REQ-${suffix}`, name_en: "Synthetic Browser Requirement", kind: "FORM" },
  });
  expect(definitionResponse.ok()).toBeTruthy();

  const ruleSetResponse = await request.post("/api/technical-rules/sets", {
    headers: owner,
    data: { code: `BROWSER-RULE-${suffix}`, name: "Synthetic Browser Rule Set", version: "1", discipline: "STRUCTURAL", jurisdiction_id: jurisdiction.id },
  });
  expect(ruleSetResponse.ok()).toBeTruthy();
});
