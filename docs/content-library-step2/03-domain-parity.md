# Content Library Step 2 — Domain Parity

Forms, Reports, and Engineering Works use the same canonical chain:

`MasterContentItem → Document → DocumentVersion`

Definitions intentionally remain on their existing separate chain:

`DefinitionEntry → DefinitionRevision`

The Dashboard and Admin Forms surfaces therefore share canonical item identity,
current-version identity, status filtering, authorization, detail, and
history. A source promoted into the library is a real master item in this
chain. A project or intake source that has not been promoted remains
transactional evidence and cannot appear as a master-library row.
