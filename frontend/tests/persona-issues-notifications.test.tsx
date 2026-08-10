import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { PersonaIssuesPage, PersonaNotificationsPage } from "../src/PersonaIssuesNotifications";

const issue = { id: "i-1", title: "SOW needs confirmation", summary: "Technical evidence is required.", domain: "PROPOSAL_TECHNICAL", severity: "BLOCKING", blocking: true, status: "OPEN", owner_persona: "ENGINEERING", actionability: "ACTIONABLE", affected_record: { label: "SYN-OPP-0001" }, deep_link: "/proposals/p-1/preparation" };
const notification = { id: "n-1", subject: "Proposal preparation ready", message: "Proposal is ready for commercial review.", event_type: "ENGINEERING_PROPOSAL_READY", domain: "PROPOSAL_TECHNICAL", severity: "ADVISORY", unread: true, actor: "Engineering", delivery_status: "DELIVERED", affected_record: { label: "SYN-OPP-0001" } };

function response(body: unknown) { return { ok: true, headers: { get: () => "application/json" }, text: async () => JSON.stringify(body) }; }

afterEach(() => vi.restoreAllMocks());

describe("persona-aware issue and notification surfaces", () => {
  it("renders engineering issues from backend list and summary projections", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(url.includes("/issues/summary") ? response({ summary: { open_issues: 1, blocking_issues: 1, work_items_affected: 1, overdue_unassigned: 0 } }) : response({ issues: [issue] }))));
    render(<PersonaIssuesPage persona="ENGINEERING" />);
    expect(await screen.findByText("Engineering issues")).toBeVisible();
    expect(screen.getByText("SOW needs confirmation")).toBeVisible();
    expect(screen.getByText("Open Issue →")).toHaveAttribute("href", "/issues/i-1");
  });

  it("keeps notification awareness separate from task completion", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(url.includes("/notifications/summary") ? response({ summary: { unread: 1, proposal_updates: 1, handoffs: 1, permit_authority_updates: 0 } }) : url.includes("observability") ? response({ delivery_failure_rate: 0, fallback_recipient_visible: false }) : response({ notifications: [notification] }))));
    render(<PersonaNotificationsPage persona="BUSINESS_DEVELOPMENT" />);
    expect(await screen.findByText("Business Development notifications")).toBeVisible();
    expect(screen.getByText("Proposal preparation ready")).toBeVisible();
    expect(screen.getByText("No delivery failures")).toBeVisible();
    await waitFor(() => expect(screen.getByText("Mark read")).toBeVisible());
  });
});
