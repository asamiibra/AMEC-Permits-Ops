# Construction Design Control

AMEC `ApprovedDesignBaseline` remains the professional-approved truth. Construction captures `AuthorityApprovedDesignSnapshot` from that baseline and then promotes a `ConstructionDesignSnapshot` with exact baseline member, rendition, and document-version IDs. A later current design supersedes the projection while prior snapshot contents remain immutable and lineage remains queryable.

Design change impact is represented by the existing `DesignChangeRequest` link on construction issues. Construction does not approve design changes or create an as-built record.
