from backend.app.runtime_provenance import get_runtime_provenance


def test_local_provenance_does_not_collapse_identities(monkeypatch):
    for key in ("VERCEL", "VERCEL_GIT_COMMIT_SHA", "WEBSITE_SITE_NAME", "WEBSITE_INSTANCE_ID"):
        monkeypatch.delenv(key, raising=False)
    assert get_runtime_provenance()["provider"] == "unknown"


def test_vercel_provenance_is_preserved(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("RELEASE_SHA", "a" * 40)
    assert get_runtime_provenance()["provider"] == "vercel"
    assert get_runtime_provenance()["sha_parity"] is True


def test_azure_provenance_is_explicit(monkeypatch):
    monkeypatch.setenv("WEBSITE_SITE_NAME", "api-preprod")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "instance")
    monkeypatch.setenv("WEBSITE_HOSTNAME", "api.example")
    monkeypatch.setenv("REGION_NAME", "qatarcentral")
    monkeypatch.setenv("WEBSITE_RESOURCE_GROUP", "rg")
    monkeypatch.setenv("RELEASE_SHA", "b" * 40)
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:" + "c" * 64)
    result = get_runtime_provenance()
    assert result["provider"] == "azure-app-service"
    assert result["release_sha"] == "b" * 40
    assert result["image_digest"].startswith("sha256:")
