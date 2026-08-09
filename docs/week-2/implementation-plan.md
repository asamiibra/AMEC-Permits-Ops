# PermitOps Week 2 implementation plan

## Objective

Extend the Week 1 modular monolith with a Tier 1, versioned configuration model; document registration and evidence handling; controlled verification; conflict and drawing checks; an expanded read-only municipality simulator; and a synthetic extraction spike guarded from real documents.

## Delivery sequence

1. Record the Week 1 regression baseline and preserve the existing project/link/audit seams.
2. Add SQLAlchemy models and Alembic migration for documents, versions, classifications, observations, assertions, configuration, dependencies, controls, spike runs, gates, and confirmations.
3. Seed a provisional `DEMO_BUILDING_PERMIT_V1` scenario and synthetic worst-case corpus. Hash document content so renamed duplicates remain deduplicated.
4. Expose explicit APIs and UI for document verification, conflict review, field authority, requirements, attachments, drawing controls, municipality configuration, spike metrics, and human submission confirmation.
5. Exercise the synthetic spike and regression suite. Keep the real-document gate false and external AI disabled.

## Non-goals

No real-document ingestion, production municipality access, credential or OTP handling, final submission, payment, signing, certification, autonomous field approval, or hardcoded acceptance thresholds.

## Exit criteria

Backend and frontend checks pass; synthetic seed is repeatable; candidate observations cannot become verified assertions without an explicit action; current assertions supersede rather than mutate history; conflicts remain open until resolved; and the real-document spike is refused without approval metadata.
