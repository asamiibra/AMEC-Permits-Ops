import { describe, expect, it } from "vitest";
import { categoryLabel, customerProductionRequirements, screenReadinessRegistry, statusLabel } from "../src/ProductionReadiness";

const readinessCopy = [
  ...customerProductionRequirements.flatMap((item) => [item.title, item.description, item.customerOwnerRole, item.internalOwnerRole, item.safeDefault || ""]),
  ...screenReadinessRegistry.flatMap((screen) => [screen.title, screen.purpose, ...screen.runtimeInputs, ...screen.runtimeOutputs, ...(screen.safetyNotes || [])]),
  ...Object.values(statusLabel).flatMap((labels) => Object.values(labels)),
  ...Object.values(categoryLabel).flatMap((labels) => Object.values(labels)),
].join(" ");

const forbiddenReadinessLanguage = [
  /signed\s+(?:production\s+)?scope/i,
  /stage\s*2\s+approval/i,
  /sign[- ]off\s*c/i,
  /\bg10\b/i,
  /formal\s+(?:production|build)\s+authorization/i,
  /technical\s+acceptance\s+signator/i,
  /formal\s+(?:sponsor|governance|change[- ]control)\s+approval/i,
  /formal\s+residual[- ]risk\s+acceptance/i,
  /governance\s+approval/i,
  /acceptance\s+signator/i,
];

describe("readiness language cleanup", () => {
  it("has no formal governance-only customer asks", () => {
    expect(customerProductionRequirements.some((item) => item.category === "GOVERNANCE")).toBe(false);
    expect(customerProductionRequirements.some((item) => item.id.startsWith("PR-GOV-"))).toBe(false);
    expect(customerProductionRequirements.length).toBe(38);
  });

  it("keeps forbidden formal language out of customer-facing readiness copy", () => {
    for (const pattern of forbiddenReadinessLanguage) expect(readinessCopy).not.toMatch(pattern);
    expect(readinessCopy).not.toMatch(/blocks production|production blocker|customer production requirements|needed from amec for production/i);
  });

  it("keeps real PermitOps human-authority and safety controls represented", () => {
    expect(readinessCopy).toMatch(/Package Approver/);
    expect(readinessCopy).toMatch(/Authorized Engineer/);
    expect(readinessCopy).toMatch(/Final Submitter/);
    expect(readinessCopy).toMatch(/commercial review/);
    expect(readinessCopy).toMatch(/contract review/);
    expect(readinessCopy).toMatch(/Finding closure authority/);
    expect(readinessCopy).toMatch(/HUMAN_SEND|Human Send/);
    expect(readinessCopy).toMatch(/MFA/);
  });
});
