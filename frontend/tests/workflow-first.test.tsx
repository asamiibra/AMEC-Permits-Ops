import { describe, expect, it } from "vitest";
import { projectNextAction, projectWorkflowStage } from "../src/WorkflowFirst";

const project = { id: "p-1", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE" };

describe("workflow-first projections", () => {
  it("projects a returned application into comments and corrections", () => {
    const application = { id: "a-1", project_id: "p-1", external_request_number: "GHCE-APP-0142", application_status: "RETURNED", repetition_count: 2, municipality: "Doha", permit_type: "Building Permit" };
    expect(projectWorkflowStage(application, [])).toBe("COMMENTS_AND_CORRECTIONS");
    const finding = { id: "f-1", project_id: "p-1", status: "OPEN", blocking: true, title: "Drawing revision requires review" };
    expect(projectWorkflowStage(application, [finding])).toBe("COMMENTS_AND_CORRECTIONS");
    expect(projectNextAction(project, application, [finding]).action_code).toBe("RESOLVE_BLOCKING_FINDING");
  });

  it("keeps stage projection deterministic and does not expose a stage edit", () => {
    const application = { id: "a-1", project_id: "p-1", external_request_number: "GHCE-APP-0142", application_status: "UNDER_REVIEW", repetition_count: 1, municipality: "Doha", permit_type: "Building Permit" };
    expect(projectWorkflowStage(application)).toBe("AUTHORITY_REVIEW");
    expect(projectNextAction(project, application).action_code).toBe("REVIEW_AUTHORITY_STATUS");
  });
});
