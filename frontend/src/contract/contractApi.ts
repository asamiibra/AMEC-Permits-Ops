import { api } from "../api";
import type { ContractData, ContractIntelligence, ContractListItem } from "./contractTypes";

export const listContracts = (query = "", filter = "ALL", signal?: AbortSignal) =>
  api<{ items: ContractListItem[]; count: number; filters?: Array<{ key: string; label: string }>; synthetic_only?: boolean }>(
    `/api/admin/contracts?q=${encodeURIComponent(query)}&filter=${encodeURIComponent(filter)}`,
    { signal },
  );

export const getContract = (contractId: string) => api<ContractData>(`/api/admin/contracts/${contractId}`);

export const getContractIntelligence = (contractId: string) =>
  api<ContractIntelligence>(`/api/admin/contracts/${contractId}/intelligence`);

export const runContractIntelligence = (contractId: string, skillId: string, idempotencyKey: string) =>
  api<Record<string, any>>(`/api/admin/contracts/${contractId}/intelligence/${skillId.replace(/^contract\./, "")}`, {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  });

export const createContract = (proposalId: string) =>
  api<ContractData>("/api/admin/contracts", {
    method: "POST",
    body: JSON.stringify({ proposal_id: proposalId }),
  });

export const contractAction = (contractId: string, action: string, body: Record<string, unknown>) =>
  api<Record<string, any>>(`/api/admin/contracts/${contractId}/${action}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
