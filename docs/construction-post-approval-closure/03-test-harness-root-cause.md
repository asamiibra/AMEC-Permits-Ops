# Test-Harness Root Cause

The entry dirty tree was caused by synthetic verification paths resolving output into repository source fixtures. The seed command wrote generated PDFs and the Week 4 workbook into canonical repository paths; fixture creation rewrote existing canonical PDFs; proposal/Synology runtime output was created under tracked mock-system roots; and the real-stack reporter wrote its JSON into a tracked prior-evidence path. These were harness and output-placement defects, not product-user changes.

The complete path-level classification is recorded in `01-dirty-tree-inventory.json` and `02-fixture-change-classification.json`.
