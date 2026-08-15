# Client Document and LPO

Client Document and LPO are first-class visible Contract inputs. Each logical source has one canonical `Document` and append-only `DocumentVersion` history. Replacing content creates the next version, marks the previous version superseded, links the current exact version through `ContractAdminEvidence`, and exposes a read-back download with version and SHA-256 headers.

The synthetic/local path stores test content in the version row and marks `read_back_verified: true` and `synthetic_only: true`. It does not claim production source-of-record ingestion. LPO requiredness is surfaced as a runtime policy; the safe default is `OWNER_DEFINITION_REQUIRED`, so the page does not create an arbitrary blocker.
