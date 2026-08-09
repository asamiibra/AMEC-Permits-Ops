# Precheck decision model v0

Precheck is an explicit synthetic state machine: `NOT_RUN → RUNNING → CLEAR` or `FINDINGS`. Findings remain linked to the observed draft and are not converted into a submission decision. Returned applications produce synthetic findings for drawing revision and missing owner evidence.

Precheck output is advisory preparation evidence. A human must inspect findings and decide the next internal action.
