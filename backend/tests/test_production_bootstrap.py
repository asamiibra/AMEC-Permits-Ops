from types import SimpleNamespace

import pytest

from backend.app import bootstrap_production


def test_production_bootstrap_rejects_non_prod(monkeypatch):
    monkeypatch.setattr(bootstrap_production, "get_settings", lambda: SimpleNamespace(app_env="AZURE-PREPROD"))
    with pytest.raises(RuntimeError, match="APP_ENV=PROD"):
        bootstrap_production.run_production_bootstrap()
