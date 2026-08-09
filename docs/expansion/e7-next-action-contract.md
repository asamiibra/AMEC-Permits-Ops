# E7 deterministic next action

Next action is derived from task status and blocking state. Blocked/disputed work resolves blockers; open work is reviewed/assigned; in-progress work continues assisted work. The result is explainable and linked to owner/context.
# E7 NextAction contract

`NextAction` is derived from canonical task state: blocked/disputed work resolves the blocker; open/acknowledged work uses its declared action or review-and-assign; in-progress work continues assisted work; completed work exposes evidence. The response includes a stable code, human label, reason, assigned role, deep link, and `deterministic: true`.
