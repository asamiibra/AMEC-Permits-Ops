# Hostile P04 gap ledger

| ID | P04C finding | Root cause | Closure |
|---|---|---|---|
| G-01 | Intake/contact/site requirements were compressed or read-only | Compact P04 presentation omitted Owner fields and write seams | Addressed in Proposal workspace and existing APIs |
| G-02 | Client name could create an implicit ClientAccount | Create path treated display text as canonical identity | Explicit client lookup/create seam added; deployed environments fail closed |
| G-03 | Technical assessment was canned PASS | UI sent a fixed status/findings payload | Actual assessment type/result/findings/evidence inputs added |
| G-04 | Scope and service eligibility used PERMITTING fixture truth | UI hard-coded an offering code | Explicit offering input and server command remain authoritative |
| G-05 | Distribution defaulted to CLIENT_PORTAL | UI and service supplied a default channel | Explicit channel/recipient/evidence fields added; service default is UNSPECIFIED |
| G-06 | LPO was a generic variance textbox | No structured comparison payload | Structured seven-field comparison contract added |
| G-07 | New Proposal visibility used UI role knowledge | Register button had no server capability projection | Register/detail capability projection added |
| G-08 | Handoff preview gates were duplicated in the UI | UI derived local gate state | Server preview now returns gate objects and mutate refreshes it |
| G-09 | Full real-stack SQL/browser qualification was absent at entry | P04 seal covered UI and test-stack evidence only | Must be executed before a PASS seal |

No unexplained missing functional surface is accepted as closed by this ledger.
