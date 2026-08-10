# Persona capability matrix

User-facing personas are OWNER, BUSINESS_DEVELOPMENT and ENGINEERING. Existing
internal roles map to these personas; SYSTEM_ADMIN remains an internal
maintenance role. Owner visibility is broad but does not grant protected
Engineering or commercial-release capabilities. BD owns intake, commercial
Proposal work, Proceed, Contract creation and Permit handoff initiation.
Engineering owns technical Proposal preparation/readiness and downstream
technical work, but cannot edit commercial Contract terms. Every write command
evaluates the server role capability.
