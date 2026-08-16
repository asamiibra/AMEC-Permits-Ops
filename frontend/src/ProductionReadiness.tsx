import { ReactNode, useEffect, useMemo, useState } from "react";
import { DashboardInputsLauncher } from "./DashboardInputs";
import { Icon } from "./Icon";

export type ReadinessStatus =
  | "NOT_REQUESTED"
  | "REQUESTED"
  | "RECEIVED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "VALIDATED"
  | "BLOCKED"
  | "NOT_APPLICABLE";
export type RequirementCategory =
  | "DATA_SOURCE"
  | "SYSTEM_ACCESS"
  | "PERMISSION"
  | "ROLE"
  | "BUSINESS_RULE"
  | "TEMPLATE"
  | "DATA_MAPPING"
  | "SECURITY_PRIVACY"
  | "REGULATION"
  | "COMMUNICATION"
  | "OPERATING_MODEL"
  | "VOLUME_SCALE"
  | "ACCEPTANCE"
  | "SUPPORT"
  | "GOVERNANCE";
export type ReadinessLocale = "en";

export type ProductionRequirement = {
  id: string;
  category: RequirementCategory;
  title: string;
  description: string;
  status: ReadinessStatus;
  requiredForProduction: boolean;
  blocksProduction: boolean;
  customerOwnerRole: string;
  internalOwnerRole: string;
  safeDefault?: string;
  evidenceRef?: string;
  appliesToScreenIds: string[];
};

export type ScreenReadinessDefinition = {
  screenId: string;
  pageKey: string;
  routePatterns: string[];
  title: string;
  purpose: string;
  runtimeInputs: string[];
  runtimeOutputs: string[];
  customerRequirementIds: string[];
  implementationStatus:
    "IMPLEMENTED" | "IMPLEMENTED_PROTOTYPE" | "FOUNDATION_ONLY" | "PLANNED";
  roleContext: string[];
  safetyNotes?: string[];
  informational?: boolean;
};

export const customerProductionRequirements: ProductionRequirement[] = [
  {
    id: "PR-BRAND-01",
    category: "TEMPLATE",
    title: "AMEC logo files",
    description:
      "Send the official high-resolution AMEC logo files for production screens and documents.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: false,
    customerOwnerRole: "AMEC brand contact",
    internalOwnerRole: "Implementation Lead",
    safeDefault:
      "Using the supplied reference image for the MVP; OFFICIAL_HIGH_RES_LOGO_REQUIRED_FROM_AMEC",
    appliesToScreenIds: [],
  },
  {
    id: "PR-SUP-01",
    category: "SUPPORT",
    title: "Main AMEC setup contact",
    description:
      "Tell us who to contact for project decisions, setup questions, and follow-up.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Main AMEC contact",
    internalOwnerRole: "Implementation Lead",
    appliesToScreenIds: [],
  },
  {
    id: "PR-SUP-02",
    category: "SUPPORT",
    title: "People who can confirm setup changes",
    description:
      "Tell us who can confirm changes to rules, templates, and configuration when questions come up.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Main AMEC contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-DATA-01",
    category: "DATA_SOURCE",
    title: "Synology project location",
    description:
      "Send the project root, folder template, naming convention, and source owner for project files.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC admin / process contact",
    internalOwnerRole: "Engineering",
    safeDefault: "Using synthetic source links",
    appliesToScreenIds: [],
  },
  {
    id: "PR-DATA-02",
    category: "DATA_SOURCE",
    title: "Project Excel workbook",
    description:
      "Send the workbook, tabs, row key, and the cells or ranges ProposalOps can update.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC admin / process contact",
    internalOwnerRole: "Owner",
    safeDefault: "Using a synthetic workbook",
    appliesToScreenIds: [],
  },
  {
    id: "PR-DATA-03",
    category: "DATA_SOURCE",
    title: "Owner and property source documents",
    description:
      "Tell us which sources to use for title deeds, ownership, QID, representation, surveys, drawings, and NOCs.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Requirement Steward",
    appliesToScreenIds: [],
  },
  {
    id: "PR-DATA-04",
    category: "DATA_SOURCE",
    title: "Real sample documents for testing",
    description:
      "Send clean, poor-scan, Arabic, stamped, and difficult examples that we can test safely.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Data Verifier",
    safeDefault: "Using synthetic documents only",
    appliesToScreenIds: [],
  },
  {
    id: "PR-DATA-05",
    category: "DATA_SOURCE",
    title: "Municipality status and comment source",
    description:
      "Tell us where application status, official comments, precheck results, and submission confirmation come from.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Portal contact",
    internalOwnerRole: "Portal Maintainer",
    safeDefault: "Using assisted/manual capture",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACC-01",
    category: "SYSTEM_ACCESS",
    title: "Project file and network access",
    description:
      "Give ProposalOps the repository, network share, file-locking, and service identity access it needs.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "IT / Security contact",
    internalOwnerRole: "Owner",
    safeDefault: "No project file access yet",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACC-02",
    category: "SYSTEM_ACCESS",
    title: "Municipality account and access",
    description:
      "Tell us which account to use, what it can prepare or read, and which status information it can access.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Portal contact",
    internalOwnerRole: "Portal Maintainer",
    safeDefault: "Using Assisted mode",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACC-03",
    category: "PERMISSION",
    title: "Municipality working mode",
    description:
      "Choose the working mode: Assisted, official API, or a controlled portal/browser workflow where available.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Portal / security contact",
    internalOwnerRole: "Portal Maintainer",
    safeDefault: "Using Assisted mode",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACC-04",
    category: "PERMISSION",
    title: "AI/provider route and data geography",
    description:
      "Tell us which project/client data ProposalOps can process, which provider and region to use, and which data should stay outside AI processing.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Security / privacy contact",
    internalOwnerRole: "Owner",
    safeDefault: "Human review and synthetic data",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACC-05",
    category: "PERMISSION",
    title: "Communication send setup",
    description:
      "Tell us the channels, sender identity, recipient list, and which messages must stay human-controlled for send.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Communications contact",
    internalOwnerRole: "System Administrator",
    safeDefault: "Draft only / Human Send",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ID-01",
    category: "SECURITY_PRIVACY",
    title: "Identity and login model",
    description:
      "Tell us the identity provider, login model, session controls, supported browsers, and network limits.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "IT / Security contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ID-02",
    category: "ROLE",
    title: "Users and role mapping",
    description:
      "Name the users and map them to preparer, verifier, engineer, approver, submitter, admin, and support roles.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ID-03",
    category: "ROLE",
    title: "Role separation and backup",
    description:
      "Tell us which roles should be separate and who can cover each step when someone is away.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ID-04",
    category: "ROLE",
    title: "Final Submitter and Authorized Engineer",
    description:
      "Name the people who perform the final Municipality submission and professional engineering decisions.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Engineering / process contact",
    internalOwnerRole: "Requirement Steward",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ID-05",
    category: "SECURITY_PRIVACY",
    title: "MFA and attended-session setup",
    description:
      "Tell us how MFA, OTP handling, re-login, timeout, takeover, and fallback should work.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "IT / portal contact",
    internalOwnerRole: "Portal Maintainer",
    safeDefault: "Attended human session",
    appliesToScreenIds: [],
  },
  {
    id: "PR-SEC-01",
    category: "SECURITY_PRIVACY",
    title: "Data handling and storage setup",
    description:
      "Tell us where project data can live, who can access it, whether AI can process each document type, retention needs, and incident contacts.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Security / privacy contact",
    internalOwnerRole: "Implementation Lead",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-01",
    category: "BUSINESS_RULE",
    title: "Field authority and conflict rules",
    description:
      "Tell us the source to trust for each important field, what to do when sources disagree, how fresh data must be, and who verifies it.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Person who confirms permit rules",
    internalOwnerRole: "Data Verifier",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-02",
    category: "BUSINESS_RULE",
    title: "Requirement and validity rules",
    description:
      "Tell us which documents and conditions are required, which expire, what depends on what, and what blocks the workflow.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Person who confirms permit rules",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-03",
    category: "BUSINESS_RULE",
    title: "Project and reference-number rules",
    description:
      "Tell us how project numbers, reference numbers, names, folders, and statuses should be created.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-04",
    category: "BUSINESS_RULE",
    title: "Findings, closure, and escalation rules",
    description:
      "Tell us the comment types, severity, blockers, closure evidence, Finding closure authority, recurrence, disputes, and escalation path.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Responsible Engineer",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-05",
    category: "BUSINESS_RULE",
    title: "Portal field and attachment mappings",
    description:
      "Tell us the page sequence, portal values, grid identity, attachment slots, save/read-back steps, and drift fallback.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Portal contact",
    internalOwnerRole: "Portal Maintainer",
    safeDefault: "Assisted entry and read-back",
    appliesToScreenIds: [],
  },
  {
    id: "PR-RULE-06",
    category: "BUSINESS_RULE",
    title: "Permit type and first project",
    description:
      "Tell us which Municipality application type and project we should configure first.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Implementation Lead",
    appliesToScreenIds: [],
  },
  {
    id: "PR-TPL-01",
    category: "TEMPLATE",
    title: "AMEC forms and templates",
    description:
      "Send the forms, undertakings, Word/PDF templates, version owner, and rules for replacing an old version.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Requirement Steward",
    appliesToScreenIds: [],
  },
  {
    id: "PR-TPL-02",
    category: "TEMPLATE",
    title: "Excel and output mappings",
    description:
      "Tell us the field-to-cell/range mappings, Arabic/English output rules, and which cells are system-owned or human-owned.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-TPL-03",
    category: "TEMPLATE",
    title: "Communication templates",
    description:
      "Send the missing-document, reference, review, invoice, handover, channel, and sender wording.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Communications contact",
    internalOwnerRole: "System Administrator",
    safeDefault: "Draft only / Human Send",
    appliesToScreenIds: [],
  },
  {
    id: "PR-MAP-01",
    category: "DATA_MAPPING",
    title: "Document and attachment matrix",
    description:
      "Tell us the document identity/version, categories, required or conditional logic, language, format, size, replacement, and deletion rules.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Person who confirms permit rules",
    internalOwnerRole: "Portal Maintainer",
    appliesToScreenIds: [],
  },
  {
    id: "PR-REG-01",
    category: "REGULATION",
    title: "Regulation sources and editions",
    description:
      "Tell us which Qatar and discipline-specific regulation sources and editions to use, and where the team can access them.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Authorized Engineer",
    internalOwnerRole: "Responsible Engineer",
    safeDefault: "Engineering authoritative review stays disabled",
    appliesToScreenIds: [],
  },
  {
    id: "PR-REG-02",
    category: "REGULATION",
    title: "Engineering disciplines and drawing formats",
    description:
      "Tell us the disciplines, drawing types, supported formats, DWF need, comment format, severity, and closure authority.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Engineering contact",
    internalOwnerRole: "Responsible Engineer",
    safeDefault: "Advisory / human review",
    appliesToScreenIds: [],
  },
  {
    id: "PR-COM-01",
    category: "COMMUNICATION",
    title: "Communication recipients and delivery follow-up",
    description:
      "Tell us the client/contact list, channels, delivery evidence, failure handling, and who to contact when a message needs follow-up.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Communications contact",
    internalOwnerRole: "Support",
    safeDefault: "Human Send",
    appliesToScreenIds: [],
  },
  {
    id: "PR-OPS-01",
    category: "OPERATING_MODEL",
    title: "Support, incidents, and maintenance",
    description:
      "Tell us the support contacts, severity levels, escalation path, support hours, and maintenance window.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "Support contact",
    internalOwnerRole: "Support",
    appliesToScreenIds: [],
  },
  {
    id: "PR-OPS-02",
    category: "VOLUME_SCALE",
    title: "Expected volume and concurrency",
    description:
      "Tell us the expected applications, users, concurrent workflows, document sizes, devices, browsers, and network conditions.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: false,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Implementation Lead",
    appliesToScreenIds: [],
  },
  {
    id: "PR-OPS-03",
    category: "OPERATING_MODEL",
    title: "Backup, restore, retention, and handover",
    description:
      "Tell us the backup/restore expectations, recovery targets, record retention, export needs, and who supports the project after handover.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "IT / Security contact",
    internalOwnerRole: "System Administrator",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACCPT-01",
    category: "ACCEPTANCE",
    title: "Test documents and expected results",
    description:
      "Send permitted real cases, clean and returned flows, redaction rules, and a reviewer who can confirm the important results.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC reviewer",
    internalOwnerRole: "Requirement Steward",
    safeDefault: "Using synthetic evidence only",
    appliesToScreenIds: [],
  },
  {
    id: "PR-ACCPT-02",
    category: "ACCEPTANCE",
    title: "Test targets and AMEC reviewer",
    description:
      "Tell us the critical fields, package checks, read-back checks, time/effort targets, and who will help review test results before go-live.",
    status: "NOT_REQUESTED",
    requiredForProduction: true,
    blocksProduction: true,
    customerOwnerRole: "AMEC reviewer",
    internalOwnerRole: "Implementation Lead",
    appliesToScreenIds: [],
  },
  {
    id: "PR-FIN-01",
    category: "ROLE",
    title: "Commercial, contract, finance, and handover contacts",
    description:
      "Only if an expanded module is used: tell us who handles commercial review, contract review, invoice follow-up, client communications, and handover.",
    status: "NOT_APPLICABLE",
    requiredForProduction: false,
    blocksProduction: false,
    customerOwnerRole: "AMEC process contact",
    internalOwnerRole: "Implementation Lead",
    safeDefault: "Foundation only / human handoff",
    appliesToScreenIds: [],
  },
];

const req = (...ids: string[]) => ids;
const baseCore = req(
  "PR-SUP-01",
  "PR-RULE-06",
  "PR-ID-01",
  "PR-ID-02",
  "PR-SEC-01",
);
const newProposalCore = req(
  "PR-SUP-01",
  "PR-ID-01",
  "PR-ID-02",
  "PR-RULE-01",
  "PR-RULE-03",
  "PR-TPL-01",
  "PR-COM-01",
);
const operational = (
  title: string,
  pageKey: string,
  screenId: string,
  purpose: string,
  inputs: string[],
  outputs: string[],
  requirements: string[] = baseCore,
  status: ScreenReadinessDefinition["implementationStatus"] = "IMPLEMENTED_PROTOTYPE",
  route = `/${pageKey}`,
): ScreenReadinessDefinition => ({
  screenId,
  pageKey,
  routePatterns: [route],
  title,
  purpose,
  runtimeInputs: inputs,
  runtimeOutputs: outputs,
  customerRequirementIds: [...new Set(requirements)],
  implementationStatus: status,
  roleContext: ["Authenticated business user"],
});

export const screenReadinessRegistry: ScreenReadinessDefinition[] = [
  operational(
    "AMEC Work",
    "my-work",
    "S01",
    "Show the work that needs the current user’s attention now.",
    [
      "Proposal, Contract and Permit work",
      "Team assignments",
      "Current workflow state",
      "Issues and blockers",
      "Handoffs",
      "Due dates",
      "Important changes",
    ],
    [
      "Prioritized work",
      "Who needs to act",
      "What is blocked",
      "What needs review",
      "Links to the exact work context",
    ],
    req(...baseCore, "PR-BRAND-01", "PR-ID-03", "PR-RULE-04", "PR-OPS-01"),
    "IMPLEMENTED",
    "/work",
  ),
  operational(
    "Proposals & Contracts",
    "permits",
    "S02",
    "Show the governed commercial register from Client source and Proposal intake through Contract and downstream Permit handoff.",
    [
      "Proposal and Contract records",
      "Client and Project context",
      "Proposal / Contract references",
      "Current lifecycle stage",
      "Handoffs and blockers",
      "Owner / team",
      "Last activity",
    ],
    [
      "Proposal and Contract portfolio",
      "Current lifecycle status",
      "Handoff visibility",
      "Direct links to Proposal / Contract work",
    ],
    req(
      ...baseCore,
      "PR-DATA-01",
      "PR-RULE-03",
      "PR-RULE-04",
      "PR-TPL-01",
      "PR-TPL-02",
      "PR-COM-01",
    ),
    "IMPLEMENTED",
    "/proposals-contracts",
  ),
  {
    ...operational(
      "New Proposal",
      "new-proposal",
      "S02A",
      "Start a Proposal from tender/client information and establish the controlled intake record before or alongside final Project setup.",
      [
        "Client information",
        "Tender / RFQ source evidence",
        "Initial Proposal details",
        "Proposal reference rules",
        "Project context if already known",
        "Business Development ownership",
      ],
      [
        "New Proposal record",
        "Controlled Proposal/reference state",
        "Verified source evidence",
        "Client / Project linkage where available",
        "Initial lifecycle state",
        "Next Proposal action",
      ],
      newProposalCore,
      "IMPLEMENTED",
      "/proposals/new",
    ),
    safetyNotes: [
      "New Proposal intake uses synthetic source evidence and simulated integrations. Downstream Permit and Municipality controls remain on Permit surfaces.",
    ],
  },
  operational(
    "Reviews",
    "reviews",
    "S03",
    "Route verification, engineering, package, handoff, and closure decisions to the right role.",
    [
      "Verification requests",
      "Review and approval tasks",
      "Finding closure evidence",
      "Submission handoffs",
    ],
    [
      "Review queue",
      "Approval, return, or rejection decision",
      "Review evidence",
    ],
    req(...baseCore, "PR-ID-03", "PR-ID-04", "PR-RULE-04"),
    "IMPLEMENTED",
    "/reviews",
  ),
  operational(
    "Issues",
    "issues",
    "S04",
    "Keep blockers, mismatches, stale state, and findings visible with ownership.",
    [
      "Blocking Findings",
      "Package blockers",
      "Portal mismatch and drift",
      "Expired dependencies and stale state",
    ],
    [
      "Issue queue",
      "Severity and blocking state",
      "Resolution and closure evidence",
    ],
    req(...baseCore, "PR-RULE-04", "PR-OPS-01"),
    "IMPLEMENTED",
    "/issues",
  ),
  operational(
    "Notifications / Communications",
    "notifications",
    "S05",
    "Show meaningful workflow and authority changes and their delivery evidence.",
    [
      "Workflow and authority events",
      "Task changes",
      "Communication drafts where implemented",
      "Recipients and delivery failures",
    ],
    [
      "Internal notifications",
      "Follow-up alerts",
      "Draft and delivery evidence",
    ],
    req(...baseCore, "PR-ACC-05", "PR-TPL-03", "PR-COM-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/notifications",
  ),
  operational(
    "Operating Guide",
    "about",
    "S06",
    "Explain the current ProposalOps workflow, capabilities, safety boundary, and broader AMEC vision.",
    [
      "Feature-status registry",
      "Workflow definition",
      "Environment status",
      "Localized content",
    ],
    [
      "User understanding",
      "Workflow and data-flow explanation",
      "Implemented-versus-planned explanation",
    ],
    req("PR-SUP-01", "PR-BRAND-01"),
    "IMPLEMENTED",
    "/operating-guide",
  ),
  operational(
    "Project & Sources",
    "PROJECT_AND_SOURCES",
    "S07",
    "Connect project identity, permit context, documents, Synology, Excel, and Municipality linkage.",
    [
      "Project and permit identity",
      "Property and ownership evidence",
      "Source documents",
      "Synology location",
      "Excel project record",
      "Municipality application context",
    ],
    [
      "Controlled source registry",
      "Document versions and evidence links",
      "Project/source linkage",
    ],
    req(
      ...baseCore,
      "PR-DATA-01",
      "PR-DATA-02",
      "PR-DATA-03",
      "PR-ACC-01",
      "PR-RULE-03",
    ),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/project-and-sources",
  ),
  operational(
    "Verify Data",
    "VERIFY_DATA",
    "S08",
    "Compare source observations and let the authorized person confirm the facts that drive the permit.",
    [
      "Field observations",
      "Document versions",
      "Candidate values and evidence",
      "Source authority",
      "Current verified facts and conflicts",
    ],
    [
      "Verified facts",
      "Verification decisions",
      "Conflict resolution and audit",
    ],
    req(...baseCore, "PR-DATA-03", "PR-DATA-04", "PR-RULE-01", "PR-ID-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/verify-data",
  ),
  operational(
    "Prepare Package",
    "PREPARE_PACKAGE",
    "S09",
    "Evaluate requirements and assemble controlled forms, Excel, drawings, attachments, and approvals.",
    [
      "Verified facts",
      "Requirements and dependencies",
      "Validity and drawings",
      "Forms, Excel, attachments",
      "Package Approver review",
    ],
    [
      "Readiness evaluation",
      "Rendered forms and outputs",
      "Package manifest and approval request",
    ],
    req(
      ...baseCore,
      "PR-RULE-02",
      "PR-TPL-01",
      "PR-TPL-02",
      "PR-MAP-01",
      "PR-ID-04",
    ),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/prepare-package",
  ),
  operational(
    "Municipality Preparation",
    "MUNICIPALITY_PREPARATION",
    "S10",
    "Prepare Municipality fields through the approved interaction mode and verify what the external system saved.",
    [
      "Approved package and preparation revision",
      "Portal field/dropdown/grid mappings",
      "Attachments",
      "External portal snapshot",
      "MFA/session state",
    ],
    [
      "Intended portal values",
      "Read-back and reconciliation evidence",
      "Portal mismatch and precheck state",
    ],
    req(
      ...baseCore,
      "PR-ACC-02",
      "PR-ACC-03",
      "PR-ID-05",
      "PR-RULE-05",
      "PR-DATA-05",
    ),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/municipality-preparation",
  ),
  operational(
    "Final Review & Human Submit",
    "FINAL_REVIEW",
    "S11",
    "Run final readiness checks and prepare the handoff for an authorized human submission.",
    [
      "Current package",
      "Package Approver decision",
      "Preparation revision and read-back",
      "Precheck and open blockers",
      "Submission handoff",
    ],
    [
      "Final readiness result",
      "Final Submitter handoff",
      "Submission confirmation workflow",
    ],
    req(...baseCore, "PR-ID-03", "PR-ID-04", "PR-ID-05", "PR-RULE-04"),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/final-review",
  ),
  operational(
    "Authority Review",
    "AUTHORITY_REVIEW",
    "S12",
    "Track submitted state, supported authority status, monitoring, and official comments.",
    [
      "Submitted snapshot and cycle",
      "External authority status",
      "Precheck and official comments",
      "Monitoring reads",
    ],
    [
      "Authority status history",
      "No-change evidence",
      "Finding candidates and notifications",
    ],
    req(...baseCore, "PR-DATA-05", "PR-ACC-02", "PR-RULE-05", "PR-COM-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/authority-review",
  ),
  operational(
    "Comments & Corrections",
    "COMMENTS_AND_CORRECTIONS",
    "S13",
    "Turn authority and internal comments into owned Findings, corrections, revisions, and resubmission readiness.",
    [
      "Official, precheck, admin, and engineering comments",
      "Evidence and corrected versions",
      "Current package/revision",
      "Recurrence history",
    ],
    [
      "Finding assignments",
      "Closure evidence and decisions",
      "New revisions, staleness, and resubmission readiness",
    ],
    req(...baseCore, "PR-RULE-04", "PR-ID-04", "PR-ACCPT-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/comments-and-corrections",
  ),
  operational(
    "History",
    "HISTORY",
    "S14",
    "Reconstruct the evidence timeline, lineage, approvals, submissions, and material decisions.",
    [
      "Document versions and verified assertions",
      "Packages and approvals",
      "Portal snapshots and prechecks",
      "Submission cycles, Findings, audit, and lineage",
    ],
    [
      "Timeline and audit reconstruction",
      "Lineage explanation",
      "Historical evidence and export where supported",
    ],
    req(...baseCore, "PR-OPS-03", "PR-RULE-04"),
    "IMPLEMENTED_PROTOTYPE",
    "/permits/:projectId/history",
  ),
  operational(
    "Administration Hub",
    "administration",
    "S15",
    "Provide privileged navigation for setup, configuration, health, and evidence.",
    ["Setup and configuration state", "Setup items", "System health and audit"],
    ["Admin navigation", "Go-live setup overview", "Configuration ownership"],
    req(...baseCore, "PR-BRAND-01", "PR-SUP-01", "PR-SUP-02", "PR-OPS-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin",
  ),
  operational(
    "Go-Live Setup",
    "go-live-readiness",
    "S26",
    "Show every practical AMEC setup item, its status, screen crosswalk, and safe fallback.",
    [
      "Setup items",
      "Screen registry and route inventory",
      "Setup statuses and notes",
      "Role visibility",
    ],
    [
      "Still-needed summary",
      "Screen-to-setup crosswalk",
      "Friendly CSV checklist",
    ],
    customerProductionRequirements.map((item) => item.id),
    "IMPLEMENTED",
    "/admin/go-live-readiness",
  ),
  operational(
    "Project Setup",
    "discovery",
    "S16",
    "Record the project, privacy, pilot, decision, and contact details needed to configure the work.",
    [
      "Setup decisions",
      "Permit type and first project",
      "Privacy and Phase 0 evidence",
      "RAID and capability notes",
    ],
    ["Project setup baseline", "Decision notes", "Setup and contact details"],
    req("PR-SUP-01", "PR-SUP-02", "PR-RULE-06", "PR-SEC-01", "PR-ACCPT-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/discovery",
  ),
  operational(
    "Configuration",
    "config",
    "S17",
    "Manage controlled environment and business configuration versions.",
    [
      "Environment and business configuration",
      "Feature policy",
      "Role and configuration state",
    ],
    ["Versioned configuration", "Ready-to-test state", "Change history"],
    req(...baseCore, "PR-SUP-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/config",
  ),
  operational(
    "Tier 1 decisions",
    "tier1",
    "S18",
    "Define the critical field, requirement, dependency, validity, and blocking decisions the workflow uses.",
    [
      "Permit type and first project",
      "Requirement and dependency rules",
      "Validity and external dependencies",
    ],
    [
      "Rule decisions",
      "Dependency and blocking rules",
      "Setup checklist logic",
    ],
    req("PR-RULE-06", "PR-RULE-02", "PR-RULE-01", "PR-ID-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/tier1",
  ),
  operational(
    "Delivery / data",
    "delivery",
    "S19",
    "Control how configured data, templates, Municipality modes, and pilot roles are assembled for delivery.",
    [
      "Verified semantic fields",
      "AMEC templates",
      "Rendering mappings and transforms",
    ],
    ["Controlled forms and projections", "Versioned delivery configuration"],
    req("PR-TPL-01", "PR-TPL-02", "PR-RULE-01", "PR-SUP-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/delivery",
  ),
  operational(
    "Attachment Rules",
    "attachments-grids",
    "S20",
    "Control attachment applicability, categories, formats, and supported grid behavior.",
    [
      "Document types",
      "Attachment categories",
      "Permit type",
      "Portal slots and persistence rules",
    ],
    ["Attachment applicability", "Validation rules", "Portal category mapping"],
    req("PR-MAP-01", "PR-RULE-05", "PR-RULE-06"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/attachments-grids",
  ),
  operational(
    "Municipality adapter / portal contract",
    "municipality",
    "S21",
    "Define bounded Municipality operations, portal semantics, drift handling, and fallback mode.",
    [
      "Municipality interaction contract",
      "Approved operations",
      "Account/session model",
      "Portal semantics",
    ],
    [
      "Versioned portal contract",
      "Allowed operations",
      "Drift and fallback state",
    ],
    req("PR-ACC-02", "PR-ACC-03", "PR-ID-05", "PR-RULE-05", "PR-DATA-05"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/municipality",
  ),
  operational(
    "Test Documents",
    "corpus",
    "S22",
    "Manage representative documents, expected results, failures, and regression evidence.",
    [
      "Real sample documents",
      "Expected results",
      "Clean and returned cases",
      "Failure cases",
    ],
    [
      "Test document set",
      "Measurements",
      "Regression evidence and known failure modes",
    ],
    req("PR-DATA-04", "PR-ACCPT-01", "PR-SEC-01", "PR-RULE-06"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/corpus",
  ),
  operational(
    "Test Targets",
    "thresholds",
    "S23",
    "Record practical test targets and evidence without inventing targets.",
    [
      "Test document results",
      "Golden Path results",
      "Business priorities and risk tolerance",
    ],
    ["Test targets", "Fallback criteria", "Test results summary"],
    req("PR-ACCPT-01", "PR-ACCPT-02", "PR-SUP-02"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/thresholds",
  ),
  operational(
    "System Health / Audit",
    "control-loop",
    "S24",
    "Inspect operational health, incident evidence, audit, and recovery signals.",
    [
      "Application and audit events",
      "Job and integration health",
      "Backup/recovery and security events",
    ],
    [
      "Operational health",
      "Alerts and incident evidence",
      "Audit investigation and recovery evidence",
    ],
    req("PR-OPS-01", "PR-OPS-03", "PR-SEC-01", "PR-SUP-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/admin/control-diagnostics",
  ),
  operational(
    "Opportunities",
    "opportunities",
    "S25",
    "Show bounded RFQ/opportunity context and BD follow-up where the expansion prototype is enabled.",
    [
      "RFQ, tender, or inquiry",
      "Client context",
      "Available project data",
      "BD follow-up state",
    ],
    ["Opportunity context", "BD tasks", "Quotation readiness signal"],
    req("PR-DATA-04", "PR-ID-02", "PR-FIN-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/opportunities",
  ),
  operational(
    "Engineering & Closeout",
    "engineering-closeout",
    "S31",
    "Show bounded engineering review and closeout foundations without claiming autonomous professional approval.",
    [
      "Drawing versions",
      "Engineering scope and discipline",
      "Regulation source and edition",
      "Prior comments and project context",
    ],
    [
      "Advisory review context",
      "Engineer disposition",
      "Comment and closeout readiness",
    ],
    req("PR-REG-01", "PR-REG-02", "PR-ID-04", "PR-ACCPT-01"),
    "IMPLEMENTED_PROTOTYPE",
    "/engineering-closeout",
  ),
  operational(
    "Expansion Foundation",
    "expansion-foundation",
    "S30",
    "Inspect shared commercial, contract, finance, communication, and handover foundation.",
    [
      "Opportunity and client context",
      "Shared evidence and templates",
      "Bounded assistant context",
    ],
    ["Foundation records", "Read-only capability status", "Handoff context"],
    req("PR-FIN-01", "PR-TPL-03"),
    "FOUNDATION_ONLY",
    "/admin/expansion-foundation",
  ),
];

const legacyPageDefinitions: Array<[string, string, string, string, string[]]> =
  [
    [
      "dashboard",
      "Legacy control room",
      "Monitor synthetic project, application, setup, and RAID signals.",
      "Dashboard metrics",
      ["PR-OPS-02"],
    ],
    [
      "projects",
      "Project register",
      "Inspect canonical project identity and linked external representations.",
      "Project and application register",
      ["PR-DATA-01", "PR-DATA-02", "PR-RULE-03"],
    ],
    [
      "documents",
      "Documents / source evidence",
      "Inspect document versions, classification, extraction, and source evidence.",
      "Document evidence and version state",
      ["PR-DATA-03", "PR-DATA-04", "PR-RULE-01"],
    ],
    [
      "conflicts",
      "Conflicts",
      "Review source conflicts and governed resolution decisions.",
      "Conflict queue and adjudication evidence",
      ["PR-RULE-01", "PR-ID-02"],
    ],
    [
      "package",
      "Package readiness",
      "Inspect controlled package readiness, blockers, forms, and approval state.",
      "Readiness and package artifacts",
      ["PR-RULE-02", "PR-TPL-01", "PR-TPL-02", "PR-MAP-01"],
    ],
    [
      "findings",
      "Findings & work",
      "Inspect findings, tasks, evidence, notifications, and closure state.",
      "Finding/task/notification evidence",
      ["PR-RULE-04", "PR-ID-04", "PR-COM-01"],
    ],
    [
      "lineage",
      "Lineage & validity",
      "Inspect source lineage, validity, material changes, and stale outputs.",
      "Lineage and validity evidence",
      ["PR-RULE-01", "PR-RULE-02", "PR-OPS-03"],
    ],
    [
      "spike",
      "Test extraction",
      "Inspect synthetic extraction results and the real-document test path.",
      "Extraction evidence and candidate metrics",
      ["PR-DATA-04", "PR-ACCPT-01", "PR-SEC-01"],
    ],
    [
      "adjudication",
      "Ground truth",
      "Record human adjudication for extraction and field decisions.",
      "Ground truth decisions",
      ["PR-DATA-04", "PR-RULE-01", "PR-ID-02"],
    ],
    [
      "analysis",
      "Test analysis",
      "Inspect extraction analysis separately from verified-value decisions.",
      "Analysis and test evidence",
      ["PR-ACCPT-01", "PR-ACCPT-02"],
    ],
    [
      "tier2",
      "Tier 2 backlog",
      "Review bounded backlog items without silently expanding the setup plan.",
      "Controlled backlog",
      ["PR-SUP-02"],
    ],
    [
      "close",
      "Go-live setup decision",
      "Record the human decision over go, fallback, or pause evidence.",
      "Decision and fallback evidence",
      ["PR-SUP-01", "PR-ACCPT-02"],
    ],
    [
      "baseline",
      "Setup baseline",
      "Inspect the frozen synthetic setup snapshot and notes.",
      "Baseline snapshot and evidence",
      ["PR-RULE-06", "PR-SUP-02"],
    ],
    [
      "signoff",
      "Commercial draft",
      "Inspect the draft commercial proposal and its boundaries.",
      "Draft proposal and exclusions",
      ["PR-FIN-01", "PR-TPL-03"],
    ],
    [
      "confirmation",
      "Submission confirmation",
      "Inspect submission confirmation evidence without treating handoff as submission.",
      "Confirmation evidence",
      ["PR-ID-04", "PR-DATA-05", "PR-RULE-05"],
    ],
    [
      "business",
      "Business case",
      "Inspect synthetic business assumptions and project setup context.",
      "Business baseline",
      ["PR-RULE-06", "PR-OPS-02"],
    ],
    [
      "business-baseline",
      "Business baseline",
      "Inspect synthetic volume, effort, and target categories.",
      "Baseline metrics",
      ["PR-OPS-02"],
    ],
    [
      "privacy",
      "Privacy & data",
      "Review data classification, privacy, location, and access decisions.",
      "Privacy decision evidence",
      ["PR-SEC-01", "PR-ACC-04"],
    ],
    [
      "volume",
      "Volume baseline",
      "Record expected applications, users, documents, and throughput assumptions.",
      "Volume baseline",
      ["PR-OPS-02"],
    ],
    [
      "inquiries",
      "Ministry inquiry",
      "Track unanswered authority and working-model questions.",
      "Inquiry and decision evidence",
      ["PR-DATA-05", "PR-ACC-03", "PR-SUP-01"],
    ],
    [
      "raid",
      "RAID log",
      "Track risks, assumptions, issues, and dependencies for go-live setup.",
      "RAID register",
      ["PR-SUP-01", "PR-SUP-02", "PR-OPS-01"],
    ],
  ];

for (const [pageKey, title, purpose, output, ids] of legacyPageDefinitions) {
  screenReadinessRegistry.push(
    operational(
      title,
      pageKey,
      `LEGACY-${pageKey.toUpperCase()}`,
      purpose,
      [
        "Current screen context",
        "Configured synthetic evidence",
        "Relevant workflow and setup state",
      ],
      [output],
      ids,
      "IMPLEMENTED_PROTOTYPE",
      pageKey === "control-loop"
        ? "/admin/control-diagnostics"
        : `/admin/${pageKey}`,
    ),
  );
}

for (const requirement of customerProductionRequirements) {
  requirement.appliesToScreenIds = screenReadinessRegistry
    .filter((screen) => screen.customerRequirementIds.includes(requirement.id))
    .map((screen) => screen.screenId);
}

export const SCREEN_ROUTE_INVENTORY = screenReadinessRegistry.map(
  ({
    screenId,
    pageKey,
    routePatterns,
    title,
    implementationStatus,
    roleContext,
  }) => ({
    screenId,
    pageKey,
    route: routePatterns[0],
    title,
    implementationStatus,
    roleVisibility: roleContext,
  }),
);

export const statusLabel: Record<
  ReadinessLocale,
  Record<ReadinessStatus, string>
> = {
  en: {
    NOT_REQUESTED: "Needed",
    REQUESTED: "Requested",
    RECEIVED: "Provided",
    UNDER_REVIEW: "Configured",
    APPROVED: "Ready",
    VALIDATED: "Tested",
    BLOCKED: "Needed",
    NOT_APPLICABLE: "Not Needed",
  },
};

export const categoryLabel: Record<
  ReadinessLocale,
  Record<RequirementCategory, string>
> = {
  en: {
    DATA_SOURCE: "Data & systems",
    SYSTEM_ACCESS: "Access & permissions",
    PERMISSION: "Access & permissions",
    ROLE: "People & roles",
    BUSINESS_RULE: "Rules & decisions",
    TEMPLATE: "Templates",
    DATA_MAPPING: "Mappings",
    SECURITY_PRIVACY: "Security / privacy",
    REGULATION: "Regulations",
    COMMUNICATION: "Communications",
    OPERATING_MODEL: "People & support",
    VOLUME_SCALE: "Setup scale",
    ACCEPTANCE: "Test data",
    SUPPORT: "Support",
    GOVERNANCE: "Setup",
  },
};

function BidiText({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

function DrawerStatus({ status }: { status: ReadinessStatus }) {
  return (
    <span
      className={`readiness-status readiness-status-${status.toLowerCase()}`}
    >
      {statusLabel.en[status]}
    </span>
  );
}

function ScreenTitle({ screen }: { screen: ScreenReadinessDefinition }) {
  return <>{screen.title}</>;
}

export function getScreenDefinition(
  pageKey: string,
  stage?: string,
): ScreenReadinessDefinition {
  const normalized = stage || pageKey;
  return (
    screenReadinessRegistry.find((screen) => screen.pageKey === normalized) ||
    screenReadinessRegistry.find((screen) => screen.pageKey === pageKey) ||
    screenReadinessRegistry[0]
  );
}

export function getScreenUnresolvedCount(screen: ScreenReadinessDefinition) {
  return screen.customerRequirementIds
    .map((id) => customerProductionRequirements.find((item) => item.id === id))
    .filter(
      (item) =>
        item &&
        [
          "NOT_REQUESTED",
          "REQUESTED",
          "RECEIVED",
          "UNDER_REVIEW",
          "BLOCKED",
        ].includes(item.status) &&
        item.requiredForProduction,
    ).length;
}

export function ReadinessDrawer({
  screenId,
  role,
  onNavigate,
}: {
  screenId: string;
  role: string;
  onNavigate: (page: string) => void;
}) {
  const screen =
    screenReadinessRegistry.find((item) => item.screenId === screenId) ||
    screenReadinessRegistry[0];
  if (screen.pageKey === "dashboard")
    return <DashboardInputsLauncher role={role} onNavigate={onNavigate} />;
  const [open, setOpen] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  useEffect(() => {
    if (open) document.querySelector<HTMLElement>(".readiness-drawer")?.focus();
  }, [open]);
  const requirements = screen.customerRequirementIds
    .map((id) => customerProductionRequirements.find((item) => item.id === id))
    .filter(Boolean) as ProductionRequirement[];
  const unresolved = getScreenUnresolvedCount(screen);
  const grouped = useMemo(
    () =>
      requirements
        .filter(
          (item) =>
            !["APPROVED", "VALIDATED", "NOT_APPLICABLE"].includes(item.status),
        )
        .reduce(
          (acc, item) => {
            (acc[item.category] ||= []).push(item);
            return acc;
          },
          {} as Record<RequirementCategory, ProductionRequirement[]>,
        ),
    [requirements],
  );
  const isAdmin = [
    "SYSTEM_ADMIN",
    "REQUIREMENT_STEWARD",
    "PORTAL_MAINTAINER",
  ].includes(role);
  return (
    <>
      <button
        className={`readiness-trigger ${unresolved ? "has-unresolved" : "validated"}`}
        onClick={() => setOpen(true)}
        aria-label="Inputs & Go-Live"
        title="Inputs & Go-Live"
      >
        <Icon name={unresolved ? "issues" : "completion"} size={15} />
        <span className="readiness-trigger-label">Inputs & Go-Live</span>
        {unresolved > 0 && <b>{unresolved}</b>}
      </button>
      {open && (
        <div
          className="readiness-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <aside
            className="readiness-drawer"
            lang="en"
            dir="ltr"
            role="dialog"
            aria-modal="true"
            aria-labelledby="readiness-drawer-title"
            tabIndex={-1}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpen(false);
            }}
          >
            <div className="readiness-drawer-head">
              <div>
                <span className="eyebrow">INPUTS &amp; GO-LIVE</span>
                <h2 id="readiness-drawer-title">
                  <ScreenTitle screen={screen} />
                </h2>
              </div>
              <button
                className="readiness-close"
                onClick={() => setOpen(false)}
                aria-label="Close Inputs & Go-Live"
              >
                <Icon name="close" size={16} />
              </button>
            </div>
            <div className="readiness-drawer-body">
              <div className="readiness-runtime-state">
                <span className="readiness-state-dot" />
                <strong>
                  {unresolved
                    ? `Demo ready · ${unresolved} go-live inputs remaining`
                    : "Demo ready · 0 go-live inputs remaining"}
                </strong>
              </div>
              <section>
                <h3>Purpose</h3>
                <p>
                  <BidiText>{screen.purpose}</BidiText>
                </p>
              </section>
              <section>
                <h3>What this screen uses</h3>
                <ul>
                  {screen.runtimeInputs.slice(0, 7).map((item) => (
                    <li key={item}>
                      <BidiText>{item}</BidiText>
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>What this screen produces</h3>
                <ul>
                  {screen.runtimeOutputs.slice(0, 6).map((item) => (
                    <li key={item}>
                      <BidiText>{item}</BidiText>
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>What we need from AMEC</h3>
                {Object.entries(grouped).map(([category, items]) => (
                  <details key={category} open={items.length <= 2}>
                    <summary>
                      <span>
                        {categoryLabel.en[category as RequirementCategory]}
                      </span>
                      <b>{items.length}</b>
                    </summary>
                    <div className="readiness-requirement-list">
                      {items.map((item) => (
                        <article key={item.id}>
                          <div className="readiness-req-top">
                            <strong>{item.title}</strong>
                            <DrawerStatus status={item.status} />
                          </div>
                          <p>{item.description}</p>
                          {item.safeDefault && (
                            <small className="readiness-safe-default">
                              {item.safeDefault}
                            </small>
                          )}
                          {showDetails && (
                            <small className="readiness-req-meta">
                              {item.customerOwnerRole} · {item.id}
                            </small>
                          )}
                        </article>
                      ))}
                    </div>
                  </details>
                ))}
              </section>
              {screen.safetyNotes?.length ? (
                <section className="readiness-boundary">
                  <h3>Important boundary</h3>
                  {screen.safetyNotes.map((note) => (
                    <p key={note}>{note}</p>
                  ))}
                </section>
              ) : (
                <section className="readiness-boundary">
                  <h3>Important boundary</h3>
                  <p>
                    Current environment is a Synthetic Prototype; final
                    Municipality submission remains human-only.
                  </p>
                </section>
              )}
            </div>
            <footer className="readiness-drawer-footer">
              <button
                className="button-secondary"
                onClick={() => setShowDetails((value) => !value)}
              >
                {showDetails ? "Hide details" : "View details"}
              </button>
              {isAdmin && (
                <button
                  className="button-primary"
                  onClick={() => {
                    setOpen(false);
                    onNavigate("go-live-readiness");
                  }}
                >
                  View all setup items
                </button>
              )}
            </footer>
          </aside>
        </div>
      )}
    </>
  );
}

export function ReadinessOverviewPage({
  onNavigate,
  role,
}: {
  onNavigate: (page: string) => void;
  role: string;
}) {
  const [filter, setFilter] = useState("ALL");
  const [category, setCategory] = useState("ALL");
  const isAdmin = [
    "SYSTEM_ADMIN",
    "REQUIREMENT_STEWARD",
    "PORTAL_MAINTAINER",
  ].includes(role);
  const rows = customerProductionRequirements.filter(
    (item) =>
      (filter === "ALL" ||
        (filter === "NEEDED" &&
          !["APPROVED", "VALIDATED", "NOT_APPLICABLE"].includes(item.status)) ||
        (filter === "GO_LIVE" && item.blocksProduction)) &&
      (category === "ALL" || item.category === category),
  );
  const screenForRequirement = (id: string) =>
    screenReadinessRegistry
      .filter((screen) => screen.customerRequirementIds.includes(id))
      .map((screen) => screen.title)
      .join(" · ");
  return (
    <div className="workflow-page readiness-overview">
      <PageIntroLike
        title="Go-Live Setup"
        description="A simple setup checklist shared by every screen. See what we use, produce, and still need from AMEC."
      />
      <div className="readiness-overview-toolbar">
        <div>
          <label>
            View
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="ALL">All setup items</option>
              <option value="NEEDED">Still needed</option>
              <option value="GO_LIVE">Needed before go-live</option>
            </select>
          </label>
          <label>
            Category
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="ALL">All categories</option>
              {Object.keys(categoryLabel.en).map((key) => (
                <option key={key} value={key}>
                  {categoryLabel.en[key as RequirementCategory]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="readiness-overview-actions">
          <button
            className="button-secondary"
            onClick={() => {
              const headers = [
                "Item",
                "Category",
                "Used on",
                "What we need from AMEC",
                "Status",
                "AMEC contact",
                "Needed before go-live?",
                "Current fallback",
                "Notes",
              ];
              const lines = rows.map((item) =>
                [
                  item.title,
                  categoryLabel.en[item.category],
                  screenForRequirement(item.id),
                  item.description,
                  statusLabel.en[item.status],
                  item.customerOwnerRole,
                  item.blocksProduction ? "Yes" : "No",
                  item.safeDefault || "—",
                  item.evidenceRef || "—",
                ]
                  .map((value) => `"${String(value).replaceAll('"', '""')}"`)
                  .join(","),
              );
              const blob = new Blob(
                [[headers.join(","), ...lines].join("\n")],
                { type: "text/csv" },
              );
              const url = URL.createObjectURL(blob);
              const anchor = document.createElement("a");
              anchor.href = url;
              anchor.download = "permitops-go-live-setup.csv";
              anchor.click();
              URL.revokeObjectURL(url);
            }}
          >
            Export CSV
          </button>
          <button
            className="button-secondary"
            onClick={() => onNavigate("administration")}
          >
            Back to Administration
          </button>
        </div>
      </div>
      <section className="readiness-summary-grid">
        <div>
          <span>Setup items</span>
          <strong>{customerProductionRequirements.length}</strong>
        </div>
        <div>
          <span>Still needed</span>
          <strong>
            {
              customerProductionRequirements.filter(
                (item) =>
                  !["APPROVED", "VALIDATED", "NOT_APPLICABLE"].includes(
                    item.status,
                  ),
              ).length
            }
          </strong>
        </div>
        <div>
          <span>Needed before go-live</span>
          <strong>
            {
              customerProductionRequirements.filter(
                (item) =>
                  item.blocksProduction &&
                  !["APPROVED", "VALIDATED", "NOT_APPLICABLE"].includes(
                    item.status,
                  ),
              ).length
            }
          </strong>
        </div>
        <div>
          <span>Current mode</span>
          <strong>Setup checklist</strong>
        </div>
      </section>
      <section className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Category</th>
              <th>Used on</th>
              <th>AMEC contact</th>
              <th>Status</th>
              <th>Go-live need</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>
                  <b>{item.title}</b>
                  <small>{item.description}</small>
                </td>
                <td>{categoryLabel.en[item.category]}</td>
                <td>{screenForRequirement(item.id)}</td>
                <td>{item.customerOwnerRole}</td>
                <td>
                  <DrawerStatus status={item.status} />
                </td>
                <td>
                  {item.blocksProduction
                    ? "Needed before go-live"
                    : "Optional for now"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {!isAdmin && (
        <div className="synthetic-note">
          Read-only summary. Setup status changes are restricted to setup
          administrators.
        </div>
      )}
    </div>
  );
}

function PageIntroLike({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page-intro">
      <div>
        <span className="eyebrow">ADMINISTRATION</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}
