# Human takeover contract

Takeover records the application/session, initiator, reason, prior state hash, and `REREAD_REQUIRED`. Resume is never blind: pause/release, human action, current read, reconciliation, then safe continuation if policy allows. No takeover record contains authentication secrets.
