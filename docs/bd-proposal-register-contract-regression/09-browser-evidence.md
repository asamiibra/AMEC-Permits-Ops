# Browser evidence

Clean in-app browser tab at `http://127.0.0.1:5179/opportunities` rendered:

- All `2`
- Need Action `2`
- Authority Review `0`
- Ready / Close `0`
- two rows: Engineering Preparation and Contract Handoff
- no Owner error alert
- no browser error or warning logs

Client search plus Contract Handoff stage filtering preserved the row and Open action. Selecting Ready / Close with the current filtered snapshot produced the governed no-records state, not a fake row or error. Direct Contract Handoff detail rendered the Proposal workspace and lifecycle without `Could not load this Proposal.`.
