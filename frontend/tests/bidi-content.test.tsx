import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BidiCode, BidiText } from "../src/BidiText";

describe("universal business-content bidi treatment", () => {
  it("keeps the application shell LTR while Arabic and mixed values follow their own direction", () => {
    render(<main lang="en" dir="ltr"><BidiText as="h2">مركز الوطن - Al Watan Center</BidiText><BidiText>مشروع 521 - Riviera Rayhaan</BidiText><BidiCode>AMEC-P-D-2026-Q-521 - عرض فني</BidiCode></main>);
    expect(screen.getByRole("main")).toHaveAttribute("dir", "ltr");
    expect(screen.getByRole("heading")).toHaveAttribute("dir", "auto");
    expect(screen.getByText("مشروع 521 - Riviera Rayhaan")).toHaveAttribute("dir", "auto");
    expect(screen.getByText("AMEC-P-D-2026-Q-521 - عرض فني")).toHaveAttribute("dir", "ltr");
  });

  it("supports Arabic form values and contenteditable paragraphs without changing labels", () => {
    render(<main dir="ltr"><label>Project name<input aria-label="Project name" dir="auto" defaultValue="مشروع الدفنة" /></label><div dir="auto" contentEditable role="textbox" aria-label="Proposal paragraph" suppressContentEditableWarning>نطاق الخدمات</div></main>);
    expect(screen.getByRole("textbox", { name: "Project name" })).toHaveAttribute("dir", "auto");
    expect(screen.getByRole("textbox", { name: "Proposal paragraph" })).toHaveAttribute("dir", "auto");
    expect(screen.getByText("Project name")).not.toHaveAttribute("dir", "auto");
    fireEvent.input(screen.getByRole("textbox", { name: "Proposal paragraph" }), { target: { textContent: "Scope of Services" } });
    expect(screen.getByRole("textbox", { name: "Proposal paragraph" })).toHaveTextContent("Scope of Services");
  });
});
