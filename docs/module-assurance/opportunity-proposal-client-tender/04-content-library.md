# Content Library proof

The canonical resolver returned exactly one current, eligible item for each Proposal purpose:

| Purpose | Resolver result | Canonical ref | Version |
|---|---|---|---|
| `BD/PROPOSAL_TEMPLATE` | `RESOLVED` | `SYN-QUAL-PROPOSAL-TEMPLATE-V1` | `1` |
| `BD/PROPOSAL_CHECKLIST` | `RESOLVED` | `SYN-QUAL-PROPOSAL-CHECKLIST-V1` | `1` |

The resolver and tests fail closed for ambiguous, wrong-purpose, inactive/superseded, unauthorized, mismatched, and arbitrary-version inputs. The Proposal projection and accepted revision pin the resolver-selected version and content hash.
