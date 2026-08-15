# Binary store contract

`BinaryStorePort` supports health, capabilities, stat, streaming read,
temporary write, mkdir, list, no-replace finalize and temporary cleanup.

The protocol is: stream/hash input → write same-share temporary object →
fresh provider read-back/hash → no-replace finalize → fresh final read-back →
publish business version. Providers normalize failures into
`StorageErrorCode`; credentials, raw paths and content are not part of errors.
