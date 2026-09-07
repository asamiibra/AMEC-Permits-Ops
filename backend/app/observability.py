"""Opt-in code-based Azure Monitor instrumentation."""

from __future__ import annotations


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
