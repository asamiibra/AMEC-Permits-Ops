import type { ProposalSourceOption } from "./types";

export const proposalSourceRegistry: ProposalSourceOption[] = [
  { key: "TENDER_EMAIL", label: "Tender Email", description: "Start from an email, subject, date, and supporting file.", acceptsFile: true, icon: "mail" },
  { key: "TENDER_DOCUMENT", label: "Tender Document", description: "Capture the tender document and its source metadata.", acceptsFile: true, icon: "document" },
  { key: "TENDER_PHOTO", label: "Tender Photo / Image", description: "Register a photographed tender or site instruction as evidence.", acceptsFile: true, icon: "image" },
  { key: "CLIENT_DATA", label: "Client Information", description: "Start from client context and a Proposal contact; no file is required.", acceptsFile: false, icon: "users" },
  { key: "NONE", label: "Start without a source", description: "Create a valid Proposal draft and add evidence later.", acceptsFile: false, icon: "empty" },
];

export const sourceLabels: Record<string, string> = Object.fromEntries(
  proposalSourceRegistry.map((item) => [item.key, item.label]),
);
