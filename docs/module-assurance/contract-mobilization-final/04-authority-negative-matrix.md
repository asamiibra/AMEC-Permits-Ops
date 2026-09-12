# Authority negative matrix

| Actor / capability posture | Review | Accept | Close / execute |
|---|---:|---:|---:|
| Owner with review capability only | ALLOW | DENY | DENY |
| Owner with acceptance capability only | DENY | ALLOW | DENY unless separately granted |
| Owner with both independently granted | ALLOW | ALLOW | Separate capability required |
| Business Development | DENY | DENY | DENY |
| Engineering | DENY | DENY | DENY |
| System/automation or AI identity | DENY for protected business action | DENY | DENY |

The matrix is enforced server-side through the canonical capability matrix. UI visibility is not used as authorization. The review-only/accept-only permutations are exercised by changing only the independent policy sets in the unit test; no client-supplied capability or actor identity is trusted.

Negative workflow coverage also includes maker/checker collision, pre-accept activation, missing executed evidence, missing client-copy distribution, wrong Contract/revision/source version, and generic close bypass attempts. Denied writes are checked for no forbidden durable state and for the appropriate denial/block code.
