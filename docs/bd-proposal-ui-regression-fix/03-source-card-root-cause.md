# Source-card root cause

The four New Proposal cards were previously selection-only controls. They did not open a source-specific intake panel, did not collect a file, and did not affect the create request. Consequently, a user could believe a Tender Email, Tender Document, Tender Photo/Image, or Client Information source had been selected while the server created only an untyped Proposal draft.

The cards are now real buttons with `aria-pressed`, one selected state, a source-specific panel, provenance fields, and a required file input when a source is selected. The UI labels map to `TENDER_EMAIL`, `TENDER_DOCUMENT`, `TENDER_PHOTO`, and `CLIENT_DATA`.
