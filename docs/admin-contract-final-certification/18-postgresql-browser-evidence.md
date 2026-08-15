# PostgreSQL and Browser Evidence

Native Homebrew PostgreSQL 16.14 was accepting connections on localhost. Fresh database: `admin_contract_final_cert_20260815`. Alembic was upgraded to and read back at `0055_bd_proposal_final_hardening`.

Results: backend `214 passed, 2 warnings`; targeted cross-module suite `32 passed, 1 warning`; frontend unit `36 passed`; frontend build passed; real-stack browser suite `37 passed` with one worker, using Vite on 5173, uvicorn on 8000, and no API interception. Accessibility, responsive, recovery, and controlled error checks were included in the browser suite.

