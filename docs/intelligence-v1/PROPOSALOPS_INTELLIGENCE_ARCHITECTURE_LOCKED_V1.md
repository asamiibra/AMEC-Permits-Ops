# ProposalOps Intelligence v1 — Locked Architecture Contract (compatibility path)

STATUS=CANONICAL_TARGET_DESIGN
VERSION=1
CHANGE_AUTHORITY=EXPLICIT_OWNER_DESIGN_AMENDMENT_REQUIRED

This compatibility-path document points to the canonical architecture contract at `docs/architecture/ProposalOps_Intelligence_Architecture_LOCKED_v1.md`. It is intentionally not a competing authority and introduces no runtime, deployment, or data authority beyond the Prompt 02 additive contract migration documented in the prompt-02 evidence directory.

The locked defaults are `canonical_write_authority=NONE` and `protected_action_authority=NONE`; human review and module-owned business transitions remain outside shared persistence.

> ProposalOps shall implement one shared governed Intelligence Platform. Document Intelligence produces provenance-preserving evidence and candidates; the Context Compiler assembles authorized current business context; module-owned skills use the shared reasoning runtime to produce analyses, drafts, recommendations and candidates. Human review, business decisions, state transitions and protected authority remain embedded in the consuming module. Shared intelligence may prepare work; it never becomes the business authority.
