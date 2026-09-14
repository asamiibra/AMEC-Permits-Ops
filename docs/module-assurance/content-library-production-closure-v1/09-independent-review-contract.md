# Independent review contract

Two fresh read-only reviewers must inspect the final exact closure head in separate checkouts. Reviewer A covers Source18 authority, ownership, authorization, TOCTOU, and audit identity. Reviewer B covers storage, upload safety, migrations, release topology, CI evidence, and production-target isolation. Reviewers must not rely on prior self-reports, must not edit/commit/push, and must return PASS or FAIL with concrete file/line evidence.

No integration or merge into `next/module-integration` is authorized until both exact-head reviews pass.
