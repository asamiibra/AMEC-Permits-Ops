# Future Branching Strategy

`main` is the one canonical integrated product baseline. Use short-lived `feature/<scope>`, `fix/<scope>`, and `chore/<scope>` branches from current main; keep scope bounded, test, merge through the normal protected workflow, and retire the branch. Do not create permanent per-module branches. Modules share models, migrations, resolvers, RBAC, audit, storage, and cross-module lifecycle, so code ownership is documented by paths and tests instead.
