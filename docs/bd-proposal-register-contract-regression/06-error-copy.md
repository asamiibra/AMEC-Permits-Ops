# Error handling

Owner-visible copy for both transport failure and strict register-contract failure is:

> We couldn't load the Proposal Register. Please retry.

The raw technical code is not rendered. The browser console receives a structured diagnostic with the endpoint and either `PROPOSAL_REGISTER_CONTRACT_INVALID` or `PROPOSAL_REGISTER_LOAD_FAILED`. Retry clears the prior error, refetches, and restores rows/counts when the response is valid.
