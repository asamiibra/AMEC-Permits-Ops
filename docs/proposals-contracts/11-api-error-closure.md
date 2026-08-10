# API error closure

The page renders a distinct `API unavailable` banner when the main register request fails and never substitutes a fake empty register. Existing global boot calls use `Promise.allSettled` for project/application data, and `/api/reconciliation/governance` is retained as a material-page dependency check. Register API 500s must be treated as release blockers.
