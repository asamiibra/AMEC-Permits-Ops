# Vercel platform facts

The current Vercel documentation confirms that Python Functions support FastAPI, respect `pyproject.toml`/`uv.lock`, and have a standard 500 MB uncompressed bundle limit. The runtime is Beta and Python 3.12 is the default. See [Python runtime](https://vercel.com/docs/functions/runtimes/python).

Vercel Functions use a read-only deployment filesystem; `/tmp` is temporary scratch and is not durable application state. FastAPI is served as a Function and uses Fluid Compute by default according to the current FastAPI guide. See [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

The current documented proxied request timeout is 120 seconds; the deployed function observed an effective 300-second timeout. See [Vercel limits](https://vercel.com/docs/limits).

Cron Jobs invoke ordinary Functions, may be delivered more than once, and Hobby cadence is once per day while Pro cadence is once per minute. See [Cron usage and pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing).
