# Browser acceptance

The frontend repair deployment reached `READY`, but opening its `/dashboard`
URL in the browser redirected to the Vercel login page. The matching backend
deployment for SHA `4976034e91a10d8ef2950a6a1f56799905bea96e` is also
`ERROR/BLOCKED` and has no runtime output. Consequently the required deployed
checks were not certified: canonical `/dashboard` V2 root, exact 14 FORME
names without synthetic prefixes, 7 Current / 7 Needs Review, truthful empty
Inactive filter, three ProposalOps functional masters, Open/Modify/History,
resolver exclusion, and Dashboard/Administration parity.

These are external deployment/authentication blockers, not evidence of a local
data failure. The local API/test evidence is recorded separately; no login,
remote seed, or browser business-parity claim was made.
