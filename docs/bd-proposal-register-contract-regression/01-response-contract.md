# Response contract

The Proposal Register now has a public backend DTO, `ProposalRegisterResponse`, with typed `ProposalRegisterRow` entries. The response includes `items` and compatibility `rows`, `count`, all four lane counts, lane definitions, predicate version, filters, supported stage options, amount/last-activity provenance, searchable fields, and the synthetic-only marker.

The frontend validates the response before rendering. Every visible row requires the identity, client/activity/stage, owner, next-action, lane, contract-eligibility, validation, and nullable timestamp fields. Invalid data clears rows and counts; it cannot be represented as a successful empty state.

The public contract is covered by `backend/tests/test_bd_proposal_ui_regression.py::test_register_public_response_contract_serializes_every_visible_row` and the malformed-response/retry tests in `frontend/tests/bd-proposal-owner-session.test.tsx`.
