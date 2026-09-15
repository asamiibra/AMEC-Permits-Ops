# Owner requirement experience map

P04 maps the Proposal-facing portion of the accepted owner requirement set into one experience contract. The 37 requirement baseline remains unchanged; this UI package does not create a second requirement registry or a second business-state store.

| Experience contract | Owner / Business Development / Engineering proof | Evidence / authority |
| --- | --- | --- |
| Register and next action | Proposal Register filters by lane, client, stage, and backend next action | Proposal register projection |
| Source-first intake | New Proposal makes Tender Email, Tender Document, Tender Photo / Image, Client Information, and no-source start explicit | Existing intake and Document/DocumentVersion paths |
| Evidence Center | Source records show source family, verification/currentness, revision, and provenance identifiers | Existing Proposal source projection |
| Scope preparation | Engineering sees pinned client request beside AMEC interpretation and separate confirmation | Human engineer / server command |
| Commercial acceptance | Working and accepted revisions remain distinct; acceptance has an explicit consequence dialog | Human commercial authority |
| Client response and LPO | Distribution, response, acceptance evidence, and structured PO/LPO comparison are separate cards | Existing protected control endpoints |
| Contract boundary | Handoff preflight states eligibility without accepting a Contract or activating a Project | Server eligibility projection |
| Intelligence | Shared candidate/work-product/currentness/citation primitives render only supplied governed objects; unavailable skill is an honest empty state | P01–P03 contracts; no new provider |

Relevant owner requirement UX orphans: `0` in the P04 field/control inventory. Existing fields and controls are either re-homed in the stage workspace or retained through existing backend projections.
