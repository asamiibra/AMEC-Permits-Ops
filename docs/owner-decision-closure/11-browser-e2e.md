# Browser E2E

The full real-stack Playwright run executed 23 tests: `20 passed, 3 failed`. Both new Owner Decision Closure tests passed. The three failures are existing baseline expectations outside this change: two expect version text that the current table renders as a numeric version, and one expects the retired “Contract workflow configuration” heading. They remain recorded rather than hidden.
