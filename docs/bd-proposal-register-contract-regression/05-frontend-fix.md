# Frontend fix

- Development API calls now use the Vite same-origin proxy, whose target follows `VITE_API_URL`; production still uses the configured API URL.
- The Proposal Register validates the typed response before state updates.
- Load failure clears rows and counts and exposes a retryable Owner-safe message.
- Stage filtering now covers the backend-supported lifecycle states, including Ready for Quotation and Quotation in Progress.
- The separate Proposals & Contracts register also maps strict contract failures to safe Owner copy while retaining technical diagnostics in the console.
