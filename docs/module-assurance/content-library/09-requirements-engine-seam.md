# Requirements Engine Seam

Requirements are owned by `shared_domain_entities.py` and the requirements/preparation services. The engine persists definitions, policy versions/items, applicability decisions, evaluations, evidence constraints and decisions. Preparation persists Project requirement instances and their source snapshots.

Content Library contributes reusable Form/Definition sources and lineage where explicitly bound. It does not calculate applicability, create a Project checklist, or replace a Project Requirement Item. The correct operational checklist projection is therefore `Project Requirement Items`, not a Content Library checklist file.
