# Browser failure adjudication

The initial no-API run failed because the backend was unavailable. A first authoritative attempt failed because the browser origin was 127.0.0.1 while CORS allowed only localhost; the server was restarted with explicit origins and the dedicated Completion scenario passed.

The broader suite was 26 passed and 6 failed. Completion-caused failures: 0. The six were unrelated Administration copy, stale health assertions expecting historical 0040/0042 heads, an unrelated engineering fixture projection, and a pre-existing universal-design permit-context timing failure. The full JSON report retains all details.
