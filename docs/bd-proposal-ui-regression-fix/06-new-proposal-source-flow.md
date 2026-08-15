# New Proposal source flow

`POST /api/bd/proposals` remains the no-initial-source draft path. A selected initial source uses multipart `POST /api/bd/proposals/intake`, which creates the Proposal and its first source in one transaction. The endpoint accepts typed source metadata and a file, returns the linked `proposal`, the created `source`, and `next_route: /opportunities/{id}`.

If a source is selected without a file, the endpoint returns typed `INITIAL_SOURCE_FILE_REQUIRED` and does not claim success. A transaction failure rolls back the Proposal and source together. No automatic Proceed, Accept, or Contract Handoff transition is performed.
