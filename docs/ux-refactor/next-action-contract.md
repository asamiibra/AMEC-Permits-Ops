# Next action contract

`NextAction` is projected by `projectNextAction()` with `action_code`, `action_label`, `reason`, `owner_role`, `stage`, and `blocking`.

Priority is deterministic: active blocking finding, returned authority comments, authority-status review, approved-history review, then source bootstrap. Consequential actions are not selected by an LLM. Cards deep-link to the permit stage that owns the action.
