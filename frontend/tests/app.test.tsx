import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";
import { LocaleProvider } from "../src/i18n";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("PermitOps shell", () => {
  it("renders the workflow-first operator shell", async () => {
    render(<LocaleProvider><App /></LocaleProvider>);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getByText("PermitOps")).toBeTruthy();
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "My Work" })).toBeTruthy();
    expect(screen.getByText("Resume permit work")).toBeTruthy();
    expect(screen.queryByText("WEEK 1 FOUNDATION")).toBeNull();
  });
});
