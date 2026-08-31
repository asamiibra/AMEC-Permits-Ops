# Retrieval and answer contract

The service is a read-only, rebuildable projection over the four canonical
Master Content libraries plus the existing DocumentVersion, FieldObservation,
VerifiedAssertion, DefinitionEntry, and DefinitionRevision chains.

- Exact references and official source identifiers rank first after Unicode/
  whitespace normalization; titles, terms, aliases, descriptions, and content
  remain searchable.
- Current versions and verified/current source status receive lifecycle rank;
  an explicitly requested historical version is replayed and cited as
  superseded.
- Every result carries canonical domain/entity IDs, document/version or
  definition revision, verification/currentness state, and a content hash when
  a document version exists.
- Permission filtering happens before source bytes or project evidence enter
  retrieval context. Project membership is explicit in the access context.
- Ties surface `AMBIGUOUS`; conflicting verified facts surface `CONFLICTING`.
  The synthetic answer seam refuses to mark either state authoritative.
- The answer seam cannot approve, sign, submit, mutate, or write canonical
  business state.
