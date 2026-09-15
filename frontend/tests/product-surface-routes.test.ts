import { describe, expect, it } from "vitest";
import { classifyPublicRoute } from "../src/domainOwnershipRoutes";
import { featureAvailability, getPrimaryNavigation } from "../src/featureAvailability";

describe("canonical product surface", () => {
  it("exposes every human delivery workspace as a deep link", () => {
    for (const path of ["/work", "/engineering", "/engineering/drawing-review", "/permits", "/permits/new", "/construction", "/completion", "/handover", "/issues", "/notifications", "/owner-decisions"]) {
      expect(classifyPublicRoute(path).allowed, path).toBe(true);
    }
  });

  it("keeps primary navigation work-oriented and historical taxonomy-free", () => {
    const labels = getPrimaryNavigation("OWNER_SPONSOR").map((item) => item.label).join(" ");
    expect(labels).not.toMatch(/week|phase|source\s*\d+/i);
    expect(getPrimaryNavigation("OWNER_SPONSOR")).toHaveLength(7);
    expect(featureAvailability.aiIntegration).toBe(false);
  });
});
