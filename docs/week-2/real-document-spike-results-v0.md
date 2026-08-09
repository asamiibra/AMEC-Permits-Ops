# Real-document spike results v0 — BLOCKED; synthetic validation completed

No real documents were used. The real-document gate is seeded false, raw access roles are empty, remote raw access is false, and external AI is disabled. Requests for `APPROVED_REAL_TEST` are refused unless explicit approval metadata exists in the TEST environment.

## Synthetic run

The Week 2 synthetic corpus contains 17 logical document versions, including poor OCR, wrong-project, expired dependency, drawing mismatch, missing-data, and renamed-duplicate cases.

| Metric | Result |
|---|---:|
| Classification agreement | 100% |
| Critical candidate agreement | 100% |
| Critical wrong candidates | 0 |
| Manual keyed percentage | 17.65% |
| Human correction percentage | 17.65% |
| Median verification time | 18 seconds |
| Evidence usability | 14 GOOD, 3 POOR |
| Failure modes | OCR_UNREADABLE: 3; WRONG_DOCUMENT_CLASS: 1 |

These are candidate extraction metrics only; they are not final verified-value correctness. All synthetic candidates remain subject to verification and no critical assertion is auto-verified.
