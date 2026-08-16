"""Resolve provider and application runtime identities without collapsing them."""

from __future__ import annotations

import os


def get_runtime_provenance() -> dict[str, object]:
    """Return normalized deployment identity and separately tracked app identity.

    Vercel system variables are authoritative for the deployed source and
    deployment instance.  RELEASE_SHA is retained only as an application
    release label for compatibility; it is never allowed to masquerade as the
    provider's deployment identity when provider metadata is available.
    """

    provider_commit_sha = os.getenv("VERCEL_GIT_COMMIT_SHA") or None
    provider_deployment_id = os.getenv("VERCEL_DEPLOYMENT_ID") or None
    provider_environment = os.getenv("VERCEL_ENV") or None
    application_release_sha = os.getenv("RELEASE_SHA") or None
    build_id = os.getenv("BUILD_ID") or provider_deployment_id
    provider_present = any(
        value is not None
        for value in (
            os.getenv("VERCEL"),
            provider_commit_sha,
            provider_deployment_id,
            provider_environment,
        )
    )

    return {
        "provider": "vercel" if provider_present else "unknown",
        "provider_commit_sha": provider_commit_sha,
        "provider_deployment_id": provider_deployment_id,
        "provider_environment": provider_environment,
        "application_release_sha": application_release_sha,
        "sha_parity": (
            provider_commit_sha == application_release_sha
            if provider_commit_sha is not None and application_release_sha is not None
            else None
        ),
        "release_sha": provider_commit_sha or application_release_sha or "UNSET",
        "build_id": build_id or "UNSET",
    }
