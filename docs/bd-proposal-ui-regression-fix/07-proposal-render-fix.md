# Proposal render fix

The canonical route is now history-aware: list open, New Proposal, back, popstate, direct navigation, and refresh all resolve through `/opportunities` and `/opportunities/{id}`. `/opportunities/new` initializes the new-intake state on direct load.

Existing detail loads have explicit loading and controlled error/not-found surfaces with Retry and list actions. Optional arrays, strings, nested configuration, and Forms-v2 fields are guarded. Valid Preparation and Contract Handoff records rendered with no Safe Recovery screen in the final real-stack run.
