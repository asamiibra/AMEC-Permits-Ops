# As-Built Design

As-Built uses existing EngineeringDeliverable, EngineeringDeliverableRevision, EngineeringRendition, DocumentVersion, EngineeringReview/finding, and ApprovalRecord patterns. AS_BUILT is a governed purpose/type, not a filename convention. Business revision identity remains separate from DocumentVersion identity.

AsBuiltBaseline is the immutable internal technical baseline for Completion preparation. It pins the ConstructionDesignSnapshot, exact EngineeringDeliverableRevision/Rendition/DocumentVersion members, AS_BUILT BuildingSnapshot(s), material/test references where material, and professional ApprovalRecords. Upload, review, professional approval, baseline approval, and authority Completion approval remain separate states. AB1 is never mutated by AB2.
