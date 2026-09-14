import type { JsonRecord, ProposalDetail } from "./types";

export const asRecord = (value: unknown): JsonRecord =>
  value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : {};

export const asList = (value: unknown): JsonRecord[] =>
  Array.isArray(value) ? value.filter((item): item is JsonRecord => Boolean(item && typeof item === "object" && !Array.isArray(item))) : [];

export const text = (value: unknown, fallback = "Not recorded"): string => {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
};

export const displayDate = (value: unknown): string => {
  if (typeof value !== "string" || !value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
};

export const labelize = (value: unknown): string => text(value, "Not set").replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());

export const control = (proposal: ProposalDetail, key: string): JsonRecord | null => {
  const value = asRecord(proposal.commercial_controls)[key];
  return Object.keys(asRecord(value)).length ? asRecord(value) : null;
};

export const currentStageNumber = (stage: string): number => {
  if (["RECEIVED", "IN_REVIEW"].includes(stage)) return 1;
  if (stage === "PROPOSAL_PREPARATION") return 2;
  if (["PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"].includes(stage)) return 3;
  if (stage === "CLIENT_RESPONSE_PENDING") return 4;
  if (["ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"].includes(stage)) return 5;
  return 1;
};

export const field = (proposal: ProposalDetail, key: string, fallback = "Not recorded"): string => text(asRecord(proposal.fields)[key], fallback);

export const safeJson = (value: unknown): JsonRecord => asRecord(value);
