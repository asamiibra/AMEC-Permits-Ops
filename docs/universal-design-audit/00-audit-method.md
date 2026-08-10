# ProposalOps Universal Design & Function Audit

## Scope

Current owner-approved truth: ProposalOps, AMEC Work, Proposals & Contracts, and the three personas Owner, Business Development, and Engineering. Permit terminology is retained only inside the downstream Permit lifecycle.

## Evidence

- 66 material route entries, 37 design contracts, and 104 applicable route/persona combinations.
- Local real-stack crawl: 3 tests passed; 0 console errors, overflow, UUID, JSON, internal actor, or forbidden-term leaks.
- Role matrix: PASS for Owner, Business Development, and Engineering.
- API failure injection: PASS with contextual error copy and retry controls.
- Deployed crawl: all three checks execute, but the deployed release is behind local; see `artifacts/universal-design-audit/deployed/`.

## Independent gates

Design conformance is measured by the contract registry, terminology detector, current/viewed stage checks, and screenshots. Functional integrity is measured by direct loads, API projections, role matrix, persistence checks, and failure injection. The result is not READY while the retired-alias contract and deployed parity remain open.
