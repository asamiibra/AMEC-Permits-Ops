# SHA parity

The release requires:

```text
EXPECTED_DEPLOY_SHA = final committed SHA
LOCAL_REMOTE_SHA_MATCH = 1
VERCEL_EXPECTED_SHA = final committed SHA
VERCEL_DEPLOYED_SHA = deployment metadata/source SHA
VERCEL_EXPECTED_SHA_MATCH = 1
```

At documentation entry, deployment parity was pending. The final section is updated only after `git rev-parse HEAD`, `git rev-parse origin/branch/ui-productionization`, the Vercel deployment metadata, and the production alias inspection agree. If Vercel does not return an exact deployed SHA, the result remains unverified rather than inferred.
