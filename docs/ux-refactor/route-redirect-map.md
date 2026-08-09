# Route redirect map

Supported workflow routes are `/work`, `/permits`, `/permits/:projectId`, `/permits/:projectId/sources`, `/permits/:projectId/verify`, `/permits/:projectId/package`, `/permits/:projectId/municipality`, `/permits/:projectId/final-review`, `/permits/:projectId/authority-review`, `/permits/:projectId/corrections`, `/permits/:projectId/history`, `/reviews`, `/issues`, `/notifications`, and `/admin/...`.

The current SPA maps these paths to the corresponding stateful view and keeps legacy module entries reachable under `/admin/<legacy-screen>`. A missing project context stays at the portfolio selector instead of creating a dead page.
