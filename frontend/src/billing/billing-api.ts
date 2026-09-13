import { api } from "../api";
import type {
  BillingCapabilityDTO,
  BillingMilestone,
  BillingPlanItem,
  BillingControlsDTO,
  BillingReportsDTO,
  CommandCenterDTO,
  InvoiceDetailDTO,
  InvoiceRegisterItem,
  InvoiceProjection,
  PaymentItem,
} from "./billing-types";

export const billingApi = {
  capabilities: () => api<BillingCapabilityDTO>("/api/billing/capabilities"),
  commandCenter: () => api<CommandCenterDTO>("/api/billing/command-center"),
  invoices: (query = "") => api<{ items: InvoiceRegisterItem[]; total: number }>(`/api/billing/invoices${query}`),
  plans: () => api<{ items: BillingPlanItem[]; total: number }>("/api/billing/plans"),
  milestones: () => api<{ items: BillingMilestone[]; total: number }>("/api/billing/milestones"),
  receivables: () => api<{ items: InvoiceProjection[]; total: number; aging_note: string }>("/api/billing/receivables"),
  payments: () => api<{ items: PaymentItem[]; total: number }>("/api/billing/payments"),
  payment: (id: string) => api<PaymentItem>(`/api/billing/payments/${id}`),
  invoice: (id: string) => api<InvoiceDetailDTO>(`/api/billing/invoices/${id}`),
  precheck: (id: string) => api<InvoiceDetailDTO["precheck"]>(`/api/billing/invoices/${id}/precheck`),
  projectFinance: (id: string) => api<Record<string, unknown>>(`/api/billing/projects/${id}/financial-projection`),
  projectPaymentHistory: (id: string) => api<{ items: PaymentItem[]; total: number }>(`/api/billing/projects/${id}/payment-history`),
  controls: () => api<BillingControlsDTO>("/api/billing/controls"),
  reports: () => api<BillingReportsDTO>("/api/billing/reports"),
};
