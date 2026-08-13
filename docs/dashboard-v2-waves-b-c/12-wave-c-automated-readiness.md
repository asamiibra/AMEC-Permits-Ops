# Wave C — automated readiness

Readiness is derived from Wave A profile state, source currency, applicability, mapping release state/checksum, validation, and required QA. It is `AUTOMATED_USE_READY` only when every blocker is cleared; otherwise it is `NEEDS_REVALIDATION` or `BLOCKED`. New source versions invalidate the prior readiness and resolver path.

Status: `IMPLEMENTED_AND_VERIFIED`.
