import pytest

from backend.app.observability import initialize_observability


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
