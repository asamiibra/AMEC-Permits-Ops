# Attention predicate contract

The visible queue and count cards use the same normalized items and `matchesView` predicate:

- `All`: every role-authorized normalized Work item plus every standalone Issue.
- `Actions`: Work items that are actionable and neither blocking nor review-only.
- `Reviews`: review/actionable-review work, including review/comment/verify language and review-state Issues.
- `Exceptions`: Issue items or blocking Work items.
- `Overdue`: an explicit overdue flag or a due date earlier than the current time.

Issue records already represented by a Work item are not duplicated; the Work row is visibly marked `ISSUE · ...` so Work and Issue semantics remain distinct. Counts are calculated from exactly the same predicate as the visible list. The rendered list is bounded to 25 rows; the current live result is below that bound.
