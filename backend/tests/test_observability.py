import pytest
import logging

from backend.app.observability import SensitiveDataFilter, initialize_observability, sanitize_log_value


class Settings:
    monitoring_mode = "DISABLED"
    applicationinsights_connection_string = ""


def test_disabled_observability_has_no_setup(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "azure.monitor.opentelemetry", None)
    initialize_observability(Settings())


def test_enabled_observability_requires_connection_string():
    value = Settings()
    value.monitoring_mode = "APPLICATION_INSIGHTS"
    with pytest.raises(ValueError, match="CONNECTION_STRING"):
        initialize_observability(value)


def test_enabled_observability_calls_official_entrypoint(monkeypatch):
    value = Settings()
    value.monitoring_mode = "APPLICATION_INSIGHTS"
    value.applicationinsights_connection_string = "InstrumentationKey=synthetic"
    called = []
    import types, sys
    module = types.ModuleType("azure.monitor.opentelemetry")
    module.configure_azure_monitor = lambda **kwargs: called.append(kwargs)
    monkeypatch.setitem(sys.modules, "azure.monitor.opentelemetry", module)
    initialize_observability(value)
    assert called == [{"connection_string": "InstrumentationKey=synthetic"}]


def test_structured_nested_pii_is_redacted_without_redacting_safe_ids():
    value = {
        "project_id": "PROJECT-42",
        "payload": {
            "QID": "28765432109",
            "passport_number": "P1234567",
            "nested": [{"residency_id": "RES-9001"}, {"permit_id": "PERMIT-7"}],
        },
    }
    rendered = sanitize_log_value(value)
    assert "28765432109" not in rendered
    assert "P1234567" not in rendered
    assert "RES-9001" not in rendered
    assert "PROJECT-42" in rendered
    assert "PERMIT-7" in rendered


@pytest.mark.parametrize(
    "message",
    [
        "validation failed qid=28765432109 passport=P1234567",
        "provider exception: sponsorship_id=SP-19 staff_id=STAFF-4",
        "HTTP 422 residency_number=RES-9001 registration_no=REG-8",
    ],
)
def test_exception_and_validation_messages_redact_labeled_pii(message):
    rendered = sanitize_log_value(message)
    assert all(secret not in rendered for secret in ("28765432109", "P1234567", "SP-19", "STAFF-4", "RES-9001", "REG-8"))


def test_filter_redacts_formatted_structured_args_and_drops_traceback():
    record = logging.LogRecord(
        "proposalops",
        logging.ERROR,
        __file__,
        1,
        "provider error: %s",
        ({"details": [{"national_id": "28765432109", "safe_id": "REQ-7"}]},),
        None,
    )
    record.exc_info = (ValueError, ValueError("passport_number=P1234567"), None)
    assert SensitiveDataFilter().filter(record)
    rendered = record.getMessage()
    assert "28765432109" not in rendered
    assert "P1234567" not in rendered
    assert "REQ-7" in rendered
    assert record.exc_info is None
    assert record.exc_text is None


def test_existing_credential_controls_remain_redacted():
    rendered = sanitize_log_value(
        "mssql+pyodbc://user:password@server/db password=secret "
        "authorization: Bearer abc123 eyJheader.payload.signature"
    )
    assert "password@server" not in rendered
    assert "password=secret" not in rendered
    assert "abc123" not in rendered
    assert "eyJheader.payload.signature" not in rendered
