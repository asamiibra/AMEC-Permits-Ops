# Route and Control Inventory

Material frontend routes are `/work`, `/proposals-contracts`, `/proposals/:id`, `/contracts/:id`, `/issues`, `/notifications`, `/admin`, and `/proposals-contracts/:projectId/project-and-sources`. The backend exposes the corresponding work, proposal/contract, persona issue/notification, administration, project, and permit workflow contracts locally.

Critical controls verified in the selected browser suite: persona switching, AMEC Work KPI/domain filters, controlled retry, Administration navigation and persistence, role denial, proposal/contract open paths, source validation, and Stage 1 confirmation persistence. The complete backend decorator inventory contains 450 registered route declarations; the artifact records the material release subset and verification state.
