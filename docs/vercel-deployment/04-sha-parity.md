# SHA parity

The release requires:

```text
EXPECTED_DEPLOY_SHA = final committed SHA
LOCAL_REMOTE_SHA_MATCH = 1
VERCEL_EXPECTED_SHA = final committed SHA
VERCEL_DEPLOYED_SHA = deployment metadata/source SHA
VERCEL_EXPECTED_SHA_MATCH = 1
```

Release SHA: `e5b916d5a81dfdd72a93a769d49d015cf2c71866`.

`git rev-parse HEAD` and `git rev-parse origin/branch/ui-productionization` matched at the release boundary. The prebuilt artifact was generated from that exact worktree and carried deployment metadata for the SHA, but Vercel rejected the final upload at the daily deployment quota before creating a READY deployment. Therefore `VERCEL_DEPLOYED_SHA` is unavailable and `VERCEL_EXPECTED_SHA_MATCH=0`; parity is not inferred from the local build or the older production alias.
