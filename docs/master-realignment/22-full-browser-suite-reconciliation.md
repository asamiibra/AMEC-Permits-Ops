# Full browser suite reconciliation

The original 19 historical browser regressions remain repaired by the focused 28/28 evidence run in `full-browser-regression-final.json`. The exact repaired specs retain their safety coverage and pass 28/28.

The current full mocked browser suite ran 113 tests: 87 passed and 26 failed. The current full real-stack suite ran 30 tests: 19 passed and 11 failed, including all six Administration checks. The broader failures are outside Administration and are stale/superseded locale, shell-navigation, owner-rehearsal, Issue, Proposal/Contract, Stage 1, accessibility, and visual assertion contracts; they remain visible in the evidence rather than being suppressed.

One previously observed genuine product failure remains separately open (not reproduced with the normal final payload): the Proposals & Contracts register can throw when `/api/proposals-main` returns an incomplete payload and `data.kpis` is absent. It was not changed by this scoped realignment.
