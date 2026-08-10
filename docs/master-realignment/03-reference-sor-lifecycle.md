# G2 — Reference and SOR lifecycle

Proposal intake may begin without a Project. New intake creates an AMEC provisional Proposal Reference (`REFERENCE_STATE=PROVISIONAL`) and writes durable evidence below the configured synthetic Proposal Intake SOR. A later canonical Project Reference is represented by `Opportunity.project_id` and the direct Contract/Permit lineage columns.

The bounded intake service hashes, writes, reads back, verifies, versions, records evidence, and audits each artifact. Duplicate hashes reuse the record; new hashes create a version. Project SOR drift blocks project writes. Promotion policy is intentionally configuration-driven and is not invented by this implementation.
