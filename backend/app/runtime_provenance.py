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

    azure_present = any(os.getenv(name) for name in ("WEBSITE_SITE_NAME", "WEBSITE_INSTANCE_ID", "WEBSITE_HOSTNAME"))
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

    if azure_present:
        release_sha = application_release_sha
        return {
            "provider": "azure-app-service",
            "application_release_sha": application_release_sha,
            "release_sha": release_sha or "UNSET",
            "image_digest": os.getenv("IMAGE_DIGEST") or "UNSET",
            "build_id": os.getenv("BUILD_ID") or "UNSET",
            "site_name": os.getenv("WEBSITE_SITE_NAME") or None,
            "region": os.getenv("REGION_NAME") or None,
            "resource_group": os.getenv("WEBSITE_RESOURCE_GROUP") or None,
            "resource_id": os.getenv("AZURE_RESOURCE_ID") or None,
            "instance_id": os.getenv("WEBSITE_INSTANCE_ID") or None,
            "hostname": os.getenv("WEBSITE_HOSTNAME") or None,
            "provider_commit_sha": None,
            "provider_deployment_id": None,
            "provider_environment": None,
            "sha_parity": None,
        }

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
