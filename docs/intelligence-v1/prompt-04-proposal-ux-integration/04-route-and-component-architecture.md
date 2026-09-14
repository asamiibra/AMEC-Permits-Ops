# Route and component architecture

Canonical routes are owned by `frontend/src/features/proposals/ProposalRoutes.tsx`:

```text
/proposals              ProposalRegisterPage
/proposals/new          NewProposalPage
/proposals/:proposalId  ProposalWorkspacePage
```

`/opportunities`, `/opportunities/new`, `/opportunities/:id`, `/bd`, and `/bd/proposals` normalize into the same route family. `App.tsx` has one active Proposal page branch and one primary `Proposals` navigation item. The legacy `ProposalsContractsPage` remains available for Contract-owned compatibility behavior; it no longer owns canonical Proposal create/detail routes.

The feature package is bounded to register, intake, workspace, shared helpers/types/registry/API adapter, and Proposal CSS. Shared Intelligence primitives live under `frontend/src/intelligence/` and are consumed by stage surfaces without introducing a Proposal-specific AI store.
