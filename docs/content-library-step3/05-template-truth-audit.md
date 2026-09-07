# Template and rendering truth audit

`MasterContentItem(FORM) → Document → immutable DocumentVersion` remains the only reusable Master Content template authority.

`FormTemplate/FormTemplateVersion` in Week 4–5 and `TemplateDefinition/TemplateVersion` in the synthetic expansion runtime are renderer configuration/metadata registries. Their persisted rows pin renderer configuration, not reusable Master Content source binaries; they do not compete with the Master Content library. Completion report rendering uses the same synthetic renderer metadata boundary.

Result: A/B renderer metadata only; competing canonical template truth count is zero. No convergence of prototype renderer configuration was warranted in this bounded step.
