from backend.app.runtime_provenance import get_runtime_provenance


def test_provider_identity_is_authoritative_when_available(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "new-sha")
    monkeypatch.setenv("VERCEL_DEPLOYMENT_ID", "dpl_new")
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("RELEASE_SHA", "new-sha")
    monkeypatch.delenv("BUILD_ID", raising=False)

    assert get_runtime_provenance() == {
        "provider": "vercel",
        "provider_commit_sha": "new-sha",
        "provider_deployment_id": "dpl_new",
        "provider_environment": "production",
        "application_release_sha": "new-sha",
        "sha_parity": True,
        "release_sha": "new-sha",
        "build_id": "dpl_new",
    }


def test_stale_application_label_is_separate_and_mismatch_is_visible(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "new-sha")
    monkeypatch.setenv("VERCEL_DEPLOYMENT_ID", "dpl_new")
    monkeypatch.setenv("RELEASE_SHA", "old-sha")

    provenance = get_runtime_provenance()

    assert provenance["release_sha"] == "new-sha"
    assert provenance["provider_commit_sha"] == "new-sha"
    assert provenance["provider_deployment_id"] == "dpl_new"
    assert provenance["application_release_sha"] == "old-sha"
    assert provenance["sha_parity"] is False


def test_explicit_build_id_remains_the_application_build_identity(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "new-sha")
    monkeypatch.setenv("VERCEL_DEPLOYMENT_ID", "dpl_new")
    monkeypatch.setenv("BUILD_ID", "build_override")
    monkeypatch.delenv("RELEASE_SHA", raising=False)

    provenance = get_runtime_provenance()

    assert provenance["build_id"] == "build_override"
    assert provenance["release_sha"] == "new-sha"
    assert provenance["application_release_sha"] is None
    assert provenance["sha_parity"] is None


def test_provider_values_are_unknown_in_local_environment(monkeypatch):
    for name in (
        "VERCEL",
        "VERCEL_GIT_COMMIT_SHA",
        "VERCEL_DEPLOYMENT_ID",
        "VERCEL_ENV",
        "BUILD_ID",
        "RELEASE_SHA",
    ):
        monkeypatch.delenv(name, raising=False)

    assert get_runtime_provenance() == {
        "provider": "unknown",
        "provider_commit_sha": None,
        "provider_deployment_id": None,
        "provider_environment": None,
        "application_release_sha": None,
        "sha_parity": None,
        "release_sha": "UNSET",
        "build_id": "UNSET",
    }
