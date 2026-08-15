# Function duration

The deployed backend function was built with an effective 300-second timeout in `iad1`. The current Vercel documentation describes configured function duration separately from the 120-second proxied request timeout; both constraints are retained in the MVP boundary. Read-only route probes completed well below those bounds, with no timeout response.
