```text
RESULT=BLOCKED
BRANCH_PUSHED=true
REMOTE_HEAD=ece16ce316cf1d5dff78c7be692436b0ff8bc2af
DISK_FREE_AT_START=1.2GB
NEW_MIGRATIONS=0
ALEMBIC_HEAD_COUNT=1
SOURCE_ROUTER_ENDPOINTS=7
PROJECT_454_TREE_FIDELITY=PASS_FIXTURE
CAPTURE_HASH_STABLE=PASS
SYNC_IDEMPOTENCY=PASS
DOWNLOAD_HASH_MATCHES=HASH_VERIFIED_BY_ROUTE
PROJECT_520_PLUS_DRAFTS=1
AUTO_PROPOSAL_CREATED_FOR_520_PLUS=0
PROJECTS_455_519_AUTO_ONBOARDED=0
SYNOLOGY_WRITE_COUNT=0
SUPPORTED_DB_PERSISTENCE=NOT_RUN
BROWSER_E2E_SOURCE_WORKSPACE=NOT_RUN
RBAC_NEGATIVES=ROUTE_DEPENDENCY_TESTED
EDITOR_OPTION_B_UNTOUCHED=true
LIVE_SYNOLOGY_SYNC=false
FIRST_BLOCKER=SUPPORTED_DATABASE_AND_BROWSER_ACCEPTANCE_UNAVAILABLE_IN_EXECUTOR
NEXT_ACTION=Run the source workspace E2E and capture persistence qualification against the repository's supported PostgreSQL runtime.
```

The deterministic fixture contains 454 (20 recursive entries, 13 files) and
520 (one source file). Syncing 454 twice produced 13 captures followed by 13
unchanged hashes. The fixture includes the expected folder names and root file
names exactly. The mounted source remains read-only and sync reports zero
writes to it; captured bytes are persisted through the canonical storage
protocol when the storage journal is available.
