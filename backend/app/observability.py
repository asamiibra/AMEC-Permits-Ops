"""Opt-in code-based Azure Monitor instrumentation."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping


_SENSITIVE_PATTERNS = (
    (re.compile(r"(?i)(?:mssql\+pyodbc|postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|sqlite)://[^\s'\"]+"), "<redacted-database-url>"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)\b(?:bearer|access_token|identity_header)\s*[=:]\s*[^\s,;]+"), "<redacted-token>"),
    (re.compile(r"(?i)(?:password|pwd|secret|client_secret|token|signature|key|smb_password|bridge_secret)\s*[=:]\s*[^\s,;]+"), "<redacted-secret>"),
    (re.compile(r"(?i)\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "<redacted-token>"),
)

# PII is redacted by field name when structured diagnostics are available.  We
# intentionally do not redact arbitrary digit strings: that would corrupt
# useful project, permit, and database diagnostics and still would not be a
# reliable passport detector.
_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "qid",
        "qid_number",
        "national_id",
        "national_identifier",
        "passport",
        "passport_no",
        "passport_number",
        "residency",
        "residency_id",
        "residency_number",
        "residence_id",
        "sponsorship",
        "sponsor_id",
        "sponsor_number",
        "staff_id",
        "employee_id",
        "engineer_id",
        "person_id",
        "regulatory_id",
        "regulatory_identifier",
        "license_no",
        "license_number",
        "registration_no",
        "registration_number",
        "classification_no",
        "classification_number",
    }
)
_SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?i)(?P<label>qid|national[_ -]?id|passport(?:[_ -]?(?:no|number))?|"
    r"residen(?:cy|ce)(?:[_ -]?(?:id|number))?|sponsor(?:ship)?(?:[_ -]?(?:id|number))?|"
    r"staff[_ -]?id|employee[_ -]?id|engineer[_ -]?id|person[_ -]?id|"
    r"regulatory[_ -]?(?:id|identifier)|(?:license|registration|classification)[_ -]?(?:no|number))"
    r"\s*[:=]\s*(?P<value>[^\s,;}}\]]+)"
)


def _field_name_is_sensitive(key: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
    return normalized in _SENSITIVE_FIELD_NAMES


def _sanitize_structured(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: "<redacted-pii>" if _field_name_is_sensitive(key) else _sanitize_structured(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_structured(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_structured(item) for item in value)
    if isinstance(value, set):
        return {_sanitize_structured(item) for item in value}
    return value


def sanitize_log_value(value: object, *, limit: int = 4000) -> str:
    text = str(_sanitize_structured(value))
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _SENSITIVE_FIELD_PATTERN.sub(
        lambda match: f"{match.group('label')}=<redacted-pii>", text
    )
    return text[:limit]


class SensitiveDataFilter(logging.Filter):
    """Keep useful diagnostics while removing credentials from retained logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Sanitize structured arguments before formatting so nested dicts
            # and lists cannot bypass the field-aware path through __str__.
            if record.args:
                if isinstance(record.args, Mapping):
                    record.args = _sanitize_structured(record.args)
                elif isinstance(record.args, tuple):
                    record.args = tuple(_sanitize_structured(item) for item in record.args)
                else:
                    record.args = _sanitize_structured(record.args)
            raw_message = _sanitize_structured(record.msg)
            record.msg = raw_message
            message = record.getMessage()
        except Exception:
            message = record.msg
        record.msg = sanitize_log_value(message)
        record.args = ()
        # A traceback can contain the original exception message and SQL URL.
        record.exc_info = None
        record.exc_text = None
        return True


def install_log_redaction_filter() -> None:
    redactor = SensitiveDataFilter()
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(existing, SensitiveDataFilter) for existing in handler.filters):
            handler.addFilter(redactor)


def initialize_observability(settings) -> None:
    mode = str(getattr(settings, "monitoring_mode", "DISABLED")).upper()
    if mode == "DISABLED":
        return
    if mode != "APPLICATION_INSIGHTS":
        raise ValueError("MONITORING_MODE must be DISABLED or APPLICATION_INSIGHTS")
    connection_string = getattr(settings, "applicationinsights_connection_string", "")
    if not connection_string:
        raise ValueError("APPLICATIONINSIGHTS_CONNECTION_STRING is required")
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)
