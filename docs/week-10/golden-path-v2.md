# Golden Path v2

Run `make golden-path-v2`. The isolated synthetic runner prepares P1/R1, captures a blocking precheck Finding, routes task/notification, material-corrects into P2/R2, rechecks clear, records an external human submission, captures a returned cycle and official comments, closes findings with role-specific evidence, asserts the negative G9 blocker, and finishes `RESUBMISSION_READY`. It emits fixture identity, revisions, packages, prechecks, findings, resolutions, gate evaluations, and safety flags.
