# Practical scale certification

Synthetic PostgreSQL dataset: 200 projects, 400 services, 400 packages, 400 revisions, 8,000 items, 400 requirements, 400 distributions, 400 receipts, and 4,000 punches. Ten representative reads each returned expected counts: all-package list 400, project-filtered list 2, workspace 20 items / 1 requirement / 1 distribution / 1 receipt / 10 punches.

Observed milliseconds (10 samples, local developer PostgreSQL; no production SLO claimed): all-package list median 12.33, p95 152.29; project list median 2.78, p95 3.73; workspace median 11.38, p95 20.60. No severe software-scale defect was observed.

