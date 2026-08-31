# Current consumer inventory

| Consumer | Classification | Connection decision |
|---|---|---|
| Master Content Forms/Reports/Engineering/Definitions reads | `CURRENT_MASTER_READ_CONSUMER` | Consume canonical item/version IDs |
| Cross-domain governed retrieval service | `CURRENT_CROSS_DOMAIN_RETRIEVAL_CONSUMER` | Single retrieval boundary |
| Synthetic governed answer seam | `CURRENT_AI_ADVISORY_CONSUMER` | Advisory, cited, non-authoritative on ambiguity/conflict |
| Existing proposal/contract/permit/preparation writers | `CURRENT_GOVERNED_WRITE_CONSUMER` | Remain on their existing governed commands; no retrieval writes |
| Future governed prefill | `NO_CURRENT_CONSUMER_TO_CONNECT` | Deferred to later branch reconciliation |
| Duplicate lexical/vector retrieval engine | `DUPLICATE_RETRIEVAL_ENGINE` | Count: 0 |
| Unclassified current consumer | `UNKNOWN` | Count: 0 |

The inventory deliberately does not connect dashboard owner reads to a second
store or mutate the accepted Step 2 product surface.
