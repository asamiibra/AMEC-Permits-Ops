# Source intake

The safe bounded archive reader, manifest reconciliation, checkpoint semantics, and FORME disposition are covered by the local source-intake tests and artifacts. The actual FORME archive is 17,009,370 bytes and exceeds the deployed 4.5 MB request limit.

There is no deployed archive-intake route and no Vercel continuation worker. Source intake is therefore compatible as a portable domain service but not enabled as a single-request Vercel transfer. The bounded future transport is direct authorized object upload followed by canonical application-controlled reconciliation and publication.
