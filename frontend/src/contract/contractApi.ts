import { api } from "../api";
import type { ContractData, ContractIntelligence, ContractIntelligenceResult, ContractListItem } from "./contractTypes";
import type { StartPrerequisites, TimingFactInput, TimingFactType, TimingRequirementInput } from "./timingTypes";

export const getStartPrerequisites = (id: string) => api<StartPrerequisites>(`/api/admin/contracts/${id}/start-prerequisites`);
export const recordTimingRequirement = (id: string, payload: TimingRequirementInput) => api<{ decision: string; evidence_id: string }>(`/api/admin/contracts/${id}/timing-requirements`, { method: "POST", body: JSON.stringify(payload) });
export const recordTimingFact = (id: string, fact: TimingFactType, payload: TimingFactInput) => api<{ decision: string; evidence_id: string }>(`/api/admin/contracts/${id}/timing-facts/${fact}`, { method: "POST", body: JSON.stringify(payload) });

export const listContracts = (query = "", filter = "ALL") =>
  api<{ items: ContractListItem[]; count: number; filters?: Array<{ key: string; label: string }>; synthetic_only?: boolean }>(
    `/api/admin/contracts?q=${encodeURIComponent(query)}&filter=${encodeURIComponent(filter)}`,
  );

export const getContract = (contractId: string) => api<ContractData>(`/api/admin/contracts/${contractId}`);

export const getContractIntelligence = (contractId: string) =>
  api<ContractIntelligence>(`/api/admin/contracts/${contractId}/intelligence`);

export const executeContractIntelligence = (contractId: string, skillId: string, idempotencyKey: string) =>
  api<ContractIntelligenceResult>(`/api/admin/contracts/${contractId}/intelligence/${encodeURIComponent(skillId)}/execute`, {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  });

export const createContract = (proposalId: string) =>
  api<ContractData>("/api/admin/contracts", {
    method: "POST",
    body: JSON.stringify({ proposal_id: proposalId }),
  });

export const contractAction = (contractId: string, action: string, body: Record<string, unknown>) =>
  api<Record<string, unknown>>(`/api/admin/contracts/${contractId}/${action}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
