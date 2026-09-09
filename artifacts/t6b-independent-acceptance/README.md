# T6-B independent acceptance

This directory durably binds the accepted T6-B producer run to a separate
stdlib-only, read-only verifier and to the exact qualified scope. The producer
artifact remains the authoritative execution evidence; the verifier records the
independent acceptance boundary and refuses to accept a different run, head,
candidate archive, schema result, cleanup result, or protected-side-effect
result.

The GitHub Actions artifact is retained separately from this source commit:

`T6B_FINAL_SQLQUAL_EXECUTION_EVIDENCE`, artifact `10082897476`, producer run
`34295201328`, attempt `1`.

No real AMEC business bytes, DSM/SMB source reads, parser executions, LLM calls,
or protected side effects were part of this acceptance.
