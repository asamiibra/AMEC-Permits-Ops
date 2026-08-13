# Migration and Backfill Plan

Migration `0044_preparation_submission_loop` is additive from `0043_project_engineering_approved_design_baseline`. It creates only runtime companion tables and indexes. It does not create live AuthorityCases, RequirementInstances, preparations, packages, submissions, findings, or outcomes from historical records.

No Proposal Accept, Project Activation, legacy authority text, folder, filename, or historical application status is treated as a live case or verified external submission. Existing history remains in its original canonical tables. Runtime rows are created only by explicit case actions.

Downgrade drops only the new companion tables in reverse dependency order. Existing Proposal, Contract, Project, Regulatory, Requirement, Form, Document, and Engineering data is untouched.
