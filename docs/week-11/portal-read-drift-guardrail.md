# Portal read drift guardrail

Every automated read performs a contract fingerprint check before interpretation. A mismatch creates `PortalDriftEvent`, marks the read policy `DRIFTED`, stops trusted parsing, preserves raw evidence metadata, emits maintainer-notification evidence, and enables assisted/manual fallback. No trusted Finding is created from a drifted parse.
