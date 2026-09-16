# Migration qualification and history finding

`CANDIDATE_SHA=f27543f0a105182152f75c4e0faf3336ff941fe0`
`CANDIDATE_TREE=c76aef5e25e0aa7fe07728dff9c7da0fd2cd5db6`
`MAIN_SHA=594b313a15cc6ade3f0505de395a5817c6337268`
`COMMAND=git show origin/main:<migration> | shasum -a 256; shasum -a 256 <migration>; git log --follow`
`ENVIRONMENT=local repository checkout`
`DB_ENGINE=PostgreSQL qualification database; target deployment is Azure SQL/SQL Server`
`REAL_AMEC_DATA_USED=false`

The candidate changes two issued migration files relative to main:

| Migration | Main SHA-256 | Candidate SHA-256 | Finding |
|---|---|---|---|
| `baseline_phase4_v36_azure_sql.py` | `b705b19dac5666fef711d3627190f7b30d3e601746e414bcc782f0e80b2585f9` | `1f2346208d6238084602fadd249573c3e2f7517533498618ed759dcad01d4dd0` | PostgreSQL explicit casts added to a repeated bind in seed SQL |
| `source18_regulatory_current_state_v1.py` | `c46642ca9ae3a265796d31fa6bd287b32466ddc226301d1ccf02ee3dc670d3ee` | `fe7f84dcef12f4e2e248ff5f9cdadabc3031f3f3807ef0abedd50ca67721614b` | Index name shortened to satisfy PostgreSQL's 63-character identifier limit |

History shows both changes are direct edits on the feature line (`f27543f`), with no forward compatibility migration or accepted rebaseline artifact found by the reference search. A clean local PostgreSQL zero-to-head run passed after the fixes, but that does not establish authority to rewrite already-issued migration bytes or prove Azure SQL execution. Therefore the terminal migration result is `BLOCKED_GOVERNANCE_REBASELINE_REQUIRED`, not PASS.

`EXIT=0` for the read-only comparison; `QUALIFICATION_RESULT=BLOCKED`
`CAPTURED=2026-09-13 Africa/Cairo`
