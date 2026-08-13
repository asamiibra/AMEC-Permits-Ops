# V2 Wave A Governance E2E

V2 is rendered by the existing canonical forms library in governance mode. The focused contract verifies:

- `Dashboard V2` identity and subtitle.
- The same four library surfaces as V1.
- `Advanced governance filters` disclosure.
- Wave A governance filter labels including Content ownership, Artifact kind, Currentness, Readiness, Quality state, Language, and Restricted sample.
- Governance detail rendering remains behind the same existing item Open action.
- `Inputs & Go-Live` is linked to the V2 route and requests `include_governance=true`.

Existing Wave A backend tests remain green for currentness, readiness recalculation, quality flags, exact source-section pinning, restricted samples, audit, and Owner-only governance writes. No Wave B/C functional control was added.
