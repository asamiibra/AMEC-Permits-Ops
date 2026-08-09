from typing import Any
from ..models import RenderingTarget, TargetRenderingRule


def render_target_value(canonical_value: Any, rule: TargetRenderingRule) -> Any:
    if canonical_value is None:
        return None if rule.null_behavior == "PRESERVE_NULL" else ""
    if rule.dropdown_code_map:
        return rule.dropdown_code_map.get(str(canonical_value), str(canonical_value))
    if rule.format_rule == "DECIMAL_2":
        return f"{float(canonical_value):.2f}" + (f" {rule.unit_rule}" if rule.unit_rule else "")
    if rule.format_rule == "DECIMAL_0":
        return f"{float(canonical_value):.0f}" + (f" {rule.unit_rule}" if rule.unit_rule else "")
    return str(canonical_value)


def rendering_preview(canonical_value: Any, rules: list[TargetRenderingRule]) -> dict[str, Any]:
    return {getattr(rule.target_system, "value", rule.target_system): {"value": render_target_value(canonical_value, rule), "target_location": rule.target_location, "rule_version": rule.version, "rule_id": rule.id} for rule in rules}
