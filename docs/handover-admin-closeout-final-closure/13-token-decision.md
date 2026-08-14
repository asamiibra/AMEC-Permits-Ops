# Token decision

- Emit/preserve `HANDOVER_ADMIN_CLOSEOUT_CODE_FROZEN`.
- Withhold `HANDOVER_ADMIN_CLOSEOUT_READY`.
- Emit `HANDOVER_ADMIN_CLOSEOUT_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`.
- Emit `FINAL_PLATFORM_CLOSURE_DEPENDENCIES_READY`.
- Preserve every blocker in `06-production-blockers.md`.

The final token is a software-domain dependency handoff. It is not production activation, owner acceptance, Synology verification, client verification, financial verification, archive verification, or final integrated platform closure.

