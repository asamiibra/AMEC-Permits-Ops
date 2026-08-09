import React from "react";
import { Week10Page } from "./Week10";
import { Week11Page } from "./Week11";
import { Week12Page } from "./Week12";
import { Week13Page } from "./Week13";
import { Week14Page } from "./Week14";

export type ReconciliationControlState = {
  packageStatus?: "BLOCKED" | "READY";
  blockedReasons?: string[];
  packageStale?: boolean;
  revisionStale?: boolean;
  currentRevision?: boolean;
  evidenceLabel?: string;
  municipalityValue?: string;
  dropdownCode?: string;
  dropdownLabel?: string;
  portalMismatch?: boolean;
  rtl?: boolean;
  findingOwner?: string;
  taskLabel?: string;
  notificationStatus?: "DELIVERED" | "FAILED";
  precheckRun?: string;
  precheckRevision?: string;
  handoffStatus?: string;
};

export function ReconciliationControls({ state = {} }: { state?: ReconciliationControlState }) {
  const blocked = state.packageStatus === "BLOCKED";
  return <><section aria-label="Weeks 1–8 control evidence" dir={state.rtl ? "rtl" : "ltr"} className="panel reconciliation-controls">
    <div data-testid="package-control"><strong>Package: {state.packageStatus || "BLOCKED"}</strong>{blocked && <ul aria-label="Package blocked reasons">{(state.blockedReasons || ["Evidence approval required"]).map(reason => <li key={reason}>{reason}</li>)}</ul>}{state.packageStatus === "READY" && <span>READY — eligible for human approval</span>}</div>
    {state.packageStale && <div role="alert">STALE PACKAGE — re-evaluation required</div>}
    {state.revisionStale && <div role="alert">STALE PREPARATION REVISION — current state is not reusable</div>}
    <div>{state.currentRevision === false ? <span>Historical revision</span> : <span>Current revision</span>} · <a href="#evidence">{state.evidenceLabel || "View evidence"}</a></div>
    <div>Assisted municipality value: <strong>{state.municipalityValue || "—"}</strong> <span>({state.dropdownCode || "CODE"} · {state.dropdownLabel || "Label"})</span></div>
    {state.portalMismatch && <div role="alert">PORTAL MISMATCH — exception requires correction</div>}
    {state.rtl && <p lang="ar">ملاحظة فنية — <bdi dir="ltr">GHCE-2026-0142</bdi></p>}
    <div>Finding owner: <strong>{state.findingOwner || "—"}</strong> · Task: <strong>{state.taskLabel || "—"}</strong></div>
    {state.notificationStatus === "FAILED" && <div role="alert">Notification FAILED — retry remains visible</div>}
    {state.notificationStatus === "DELIVERED" && <div>Notification DELIVERED</div>}
    <div>Precheck run: <bdi dir="ltr">{state.precheckRun || "—"}</bdi> · revision: <bdi dir="ltr">{state.precheckRevision || "—"}</bdi></div>
    <div>Handoff: <strong>{state.handoffStatus || "HUMAN SUBMISSION REQUIRED"}</strong></div>
    <p id="evidence" className="muted">Evidence links remain inspectable; human-owned Excel regions are protected.</p>
    <span data-testid="no-final-submit">No final-submit control exists in this operator surface.</span>
  </section><div id="week10-control-loop"><Week10Page /></div><div id="week11-monitoring"><Week11Page /></div><div id="week12-assisted-maturity"><Week12Page /></div><div id="week13-operations"><Week13Page /></div><div id="week14-acceptance"><Week14Page /></div></>;
}
