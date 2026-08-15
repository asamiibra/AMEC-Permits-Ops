# Browser evidence

Command used for the valid isolated run:

```text
BASE_URL=http://127.0.0.1:5174 API_BASE_URL=http://127.0.0.1:8000 npm run browser-real-stack -- home-navigation-reorganization.spec.ts dashboard-v1-v2-split.spec.ts
```

Result: 10 tests passed across the new Home suite and the updated Dashboard split suite. The first attempt on port 5173 was discarded because it reused a stale server from another worktree; it is not acceptance evidence for this change.
