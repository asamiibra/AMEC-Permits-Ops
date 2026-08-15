# promotion protocol

Promotion is copy-only. The exact observed member bytes are hashed, passed to the existing Master Content service, written to the managed provider through a temporary object, independently read back and hashed, finalized to a no-replace destination, independently read back again, and only then published in the database. The source archive remains at its original location.

The promotion idempotency key is `source-intake:<item id>`. Already-published items are returned without a second Master Content record. Needs-review items use the same binary verification protocol and are excluded by the existing normal resolver until reviewed.
