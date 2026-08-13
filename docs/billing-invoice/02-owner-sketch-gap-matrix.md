# Owner-sketch gap matrix

| Intent | Resolution |
|---|---|
| Invoice list lanes | Implemented as derived invoice stage/status lanes. |
| Contract/Project context | Exact ContractRevision and canonical Project are pinned; pre-activation context remains explicit. |
| Approval Ref / Reference No. / LC No. | Typed `InvoiceReference`; LC semantics remain unresolved/configurable. |
| Accept | Human-only immutable `InvoiceAcceptRecord`; Accept is not Issue. |
| Download Invoice | Exact issued `RenderedArtifact`; draft output is labeled draft. |
| Amount and line grid | Decimal deterministic calculation with INFORMATION/CHARGE/ADJUSTMENT roles. |
| Deduction-like sketch field | Adjustment lines disabled by safe default. |
| Automatic | Optional AUTO_PREPARE_DRAFT only; no auto-accept, issue, or paid state. |
