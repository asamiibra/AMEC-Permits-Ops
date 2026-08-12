# RBAC and technical-fact protection

Owner Decision reads and writes use the existing Owner-only dependency. Engineer and other non-Owner roles cannot mutate decisions. The technical Synology fact has no Owner confirmation action: manual verification returns `SYNOLOGY_MANUAL_VERIFICATION_ZERO`. The only supported path is external technical verification followed by a system-controlled update.
