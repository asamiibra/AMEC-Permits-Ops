import { api } from "../../api";
import type { ProposalDetail, ProposalRegisterResponse, ProposalRole } from "./types";

export const proposalHeaders = (role: ProposalRole): HeadersInit => ({ "X-Dev-Role": role });

export async function loadProposalRegister(role: ProposalRole, query: URLSearchParams): Promise<ProposalRegisterResponse> {
  return api<ProposalRegisterResponse>(`/api/bd/proposals?${query.toString()}`, { headers: proposalHeaders(role) });
}
export async function loadProposal(role: ProposalRole, id: string): Promise<ProposalDetail> {
  return api<ProposalDetail>(`/api/bd/proposals/${id}`, { headers: proposalHeaders(role) });
}

export async function proposalCommand<T>(role: ProposalRole, id: string, path: string, payload?: unknown): Promise<T> {
  return api<T>(`/api/bd/proposals/${id}/${path}`, {
    method: "POST",
    headers: { ...proposalHeaders(role), "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
}
