import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationBell } from "../src/NotificationBell";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = new URL(String(input), window.location.origin);
    const body = url.pathname.endsWith("/summary")
      ? { summary: { unread: 1 } }
      : { notifications: [{ id: "n-1", subject: "Review proposal evidence", message: "Proposal P-001 needs attention.", deep_link: "/opportunities/P-001", unread: true }] };
    return Promise.resolve({ ok: true, headers: { get: () => "application/json" }, text: async () => JSON.stringify(body) });
  }));
});

describe("header notification bell", () => {
  it("keeps notification visibility in the header and preserves deep links", async () => {
    render(<NotificationBell persona="OWNER" />);
    await waitFor(() => expect(screen.getByLabelText("1 unread notifications")).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    await waitFor(() => expect(screen.getByText("Review proposal evidence")).toBeVisible());
    expect(screen.getByRole("link", { name: /Review proposal evidence/ })).toHaveAttribute("href", "/opportunities/P-001");
    expect(screen.getByRole("link", { name: /View all notifications/ })).toHaveAttribute("href", "/notifications");
    expect(screen.queryByRole("navigation", { name: /notifications/i })).toBeNull();
  });
});
