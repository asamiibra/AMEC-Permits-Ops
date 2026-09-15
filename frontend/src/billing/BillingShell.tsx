import { useEffect, useState } from "react";
import { billingApi } from "./billing-api";
import { BillingCommandCenter } from "./BillingCommandCenter";
import { BillingRegisters } from "./BillingRegisters";
import { InvoiceWorkspace } from "./InvoiceWorkspace";
import { BillingPlanWorkspace, PaymentWorkspace, ProjectFinanceWorkspace } from "./BillingDetailWorkspaces";
import type { BillingCapabilityDTO, CommandCenterDTO, InvoiceDetailDTO } from "./billing-types";
import { StateMessage } from "./components/BillingPrimitives";
import { ApiError } from "../api";
import "./billing-experience.css";

type View = "center" | "plans" | "milestones" | "invoices" | "receivables" | "payments" | "controls" | "reports";

function billingErrorMessage(cause: unknown): string {
  if (cause instanceof ApiError && cause.status === 401) return "Your session has expired. Sign in again to reopen Billing.";
  if (cause instanceof ApiError && cause.status === 403) return "Your role does not have Billing access in this workspace. Contact an Owner or system administrator if access is required.";
  return "Billing could not be loaded right now. Retry the workspace, and contact support if the issue continues.";
}

const viewForPath = (path: string): View => path === "/billing" ? "center" : path.startsWith("/billing/plans") ? "plans" : path.startsWith("/billing/milestones") ? "milestones" : path.startsWith("/billing/receivables") ? "receivables" : path.startsWith("/billing/payments") ? "payments" : path.startsWith("/billing/controls") ? "controls" : path.startsWith("/billing/reports") ? "reports" : "invoices";

export function BillingShell() {
  const [path, setPath] = useState(window.location.pathname);
  const [capabilities, setCapabilities] = useState<BillingCapabilityDTO | null>(null);
  const [capabilityError, setCapabilityError] = useState("");
  const [center, setCenter] = useState<CommandCenterDTO | null>(null);
  const [centerError, setCenterError] = useState("");
  const [centerLoading, setCenterLoading] = useState(true);
  const [detail, setDetail] = useState<InvoiceDetailDTO | null>(null);
  const invoiceId = path.startsWith("/billing/invoices/") ? path.split("/")[3] : "";
  const planId = path.startsWith("/billing/plans/") ? path.split("/")[3] : "";
  const paymentId = path.startsWith("/billing/payments/") ? path.split("/")[3] : "";
  const projectId = path.startsWith("/billing/projects/") ? path.split("/")[3] : "";
  const loadCapabilities = () => { setCapabilityError(""); void billingApi.capabilities().then(setCapabilities).catch((cause: unknown) => { setCapabilities(null); setCapabilityError(billingErrorMessage(cause)); }); };
  const loadCenter = () => { setCenterLoading(true); setCenterError(""); void billingApi.commandCenter().then(setCenter).catch((cause: unknown) => setCenterError(billingErrorMessage(cause))).finally(() => setCenterLoading(false)); };
  const loadDetail = () => { if (!invoiceId) { setDetail(null); return; } void billingApi.invoice(invoiceId).then(setDetail).catch(() => setDetail(null)); };
  useEffect(() => { loadCapabilities(); }, []);
  useEffect(() => { const sync = () => setPath(window.location.pathname); window.addEventListener("popstate", sync); return () => window.removeEventListener("popstate", sync); }, []);
  useEffect(() => { if (capabilities) loadCenter(); }, [capabilities]);
  useEffect(() => { loadDetail(); }, [invoiceId]);
  const navigate = (next: string) => { window.history.pushState({}, "", next); window.dispatchEvent(new PopStateEvent("popstate")); };
  if (capabilityError || !capabilities) return <div className="billing-page"><StateMessage kind={capabilityError ? "denied" : "loading"} title={capabilityError ? "Billing unavailable" : "Resolving Billing authority"} detail={capabilityError || "The workspace stays closed until the server capability projection is available."} onRetry={capabilityError ? loadCapabilities : undefined} /></div>;
  if (invoiceId) return detail ? <InvoiceWorkspace detail={detail} capabilities={capabilities} onBack={() => navigate("/billing/invoices")} onRefresh={loadDetail} /> : <StateMessage kind="error" title="Invoice workspace unavailable" detail="The invoice is not available in the current Billing scope." onRetry={loadDetail} />;
  if (planId) return <BillingPlanWorkspace planId={planId} capabilities={capabilities} onOpen={navigate} />;
  if (paymentId) return <PaymentWorkspace paymentId={paymentId} capabilities={capabilities} onOpen={navigate} />;
  if (projectId) return <ProjectFinanceWorkspace projectId={projectId} onOpen={navigate} />;
  const view = viewForPath(path);
  return <div className="billing-page"><nav className="billing-local-nav" aria-label="Billing and Finance"><button className={view === "center" ? "active" : ""} onClick={() => navigate("/billing")}>Command Center</button><button className={view === "plans" ? "active" : ""} onClick={() => navigate("/billing/plans")}>Billing &amp; Milestones</button><button className={view === "invoices" ? "active" : ""} onClick={() => navigate("/billing/invoices")}>Invoices</button><button className={view === "receivables" ? "active" : ""} onClick={() => navigate("/billing/receivables")}>Receivables</button><button className={view === "payments" ? "active" : ""} onClick={() => navigate("/billing/payments")}>Payments &amp; Credits</button><button className={view === "controls" ? "active" : ""} onClick={() => navigate("/billing/controls")}>Controls</button><button className={view === "reports" ? "active" : ""} onClick={() => navigate("/billing/reports")}>Reports</button></nav>{view === "center" ? <BillingCommandCenter capabilities={capabilities} onOpen={navigate} onRetry={loadCenter} data={center} error={centerError} loading={centerLoading} /> : <BillingRegisters view={view} capabilities={capabilities} onOpen={navigate} />}</div>;
}
