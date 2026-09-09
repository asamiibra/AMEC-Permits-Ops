"""Opt-in code-based Azure Monitor instrumentation."""

from __future__ import annotations

import logging
import re


_SENSITIVE_PATTERNS = (
    (re.compile(r"(?i)(?:mssql\+pyodbc|postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|sqlite)://[^\s'\"]+"), "<redacted-database-url>"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)\b(?:bearer|access_token|identity_header)\s*[=:]\s*[^\s,;]+"), "<redacted-token>"),
    (re.compile(r"(?i)(?:password|pwd|secret|client_secret|token|signature|key|smb_password|bridge_secret)\s*[=:]\s*[^\s,;]+"), "<redacted-secret>"),
    (re.compile(r"(?i)\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "<redacted-token>"),
)


def sanitize_log_value(value: object, *, limit: int = 4000) -> str:
    text = str(value)
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:limit]


class SensitiveDataFilter(logging.Filter):
    """Keep useful diagnostics while removing credentials from retained logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
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
