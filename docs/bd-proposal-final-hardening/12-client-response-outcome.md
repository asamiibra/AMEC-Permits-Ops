# Client response and commercial outcome

Client response is recorded as external evidence with response type, accepted revision pointer, notes, evidence reference, actor/time, and idempotency key. `CHANGE_REQUESTED` moves the Proposal to a response-pending lane without collapsing into AMEC Accept.

Commercial outcome is a separate typed record (`WON`, `LOST`, `WITHDRAWN`, `EXPIRED`, `CONVERTED`, `SUPERSEDED`). Ready/Close lane membership remains separate from outcome; terminal loss/withdrawal/expiry closes lifecycle without rewriting history.
