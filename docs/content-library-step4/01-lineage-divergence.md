# Deployment lineage divergence

The known Azure/SQL lineage is `02b797d323acafb754f579331d2d1dc022b647b2`.
The latest visible Azure compatibility branch is
`b6328317abc57d2b06b249e68dd9ad41d63ad6c1`.

Against the known Azure SQL/token closure SHA, the exact comparison is:

| Relationship | Evidence |
| --- | --- |
| Merge base | `fde6eb9d02bbbc9b3c032598b45945cb3e4d0de3` |
| Azure commits not on Step 3 | 196 |
| Step 3 commits not on Azure | 5 |
| Relationship | divergent, non-ancestor-compatible |

The Content Library-side commit count is the verified `rev-list --left-right`
result required by the brief. The semantic Content Library commits are
`d913f62`, `686ddbf`, `d8445c90`, and `46934d09`; the shared baseline is not
itself a Content Library change. All paths and their phase classifications are
listed in the delta manifest.

The Vercel read-only health response identified provider commit
`3474b35a13d27f0010ec5d03dd4a2f361ac6774d`, application release
`26eef3df9dea6c8f1bfb763db8a43192223f3e3f`, and deployment
`dpl_5CZpxueesRMNEewRHYVScf2NmVcT`. It reported `environment=TEST`, not an
Azure-preprod deployment, so it is not an integration target.
