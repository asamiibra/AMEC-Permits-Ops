# Dirty-Tree Fixture Classification

Every one of the 140 entry paths is classified. No path was treated as unrelated local work, unknown, or sensitive data. The dirty set is synthetic/test-generated residue.

- `C_GENERATED_TEST_OUTPUT`: the tracked Playwright JSON report.
- `D_GENERATED_RUNTIME_OUTPUT`: untracked mock-Synology master-content and proposal-intake output.
- `F_TEST_HARNESS_MUTATION_OF_CANONICAL_FIXTURE`: the tracked workbook, tracked PDFs, tracked synthetic PDFs, and deleted tracked proposal fixture.

The generator/test/browser root causes and exact path-level classifications are in `02-fixture-change-classification.json`.
