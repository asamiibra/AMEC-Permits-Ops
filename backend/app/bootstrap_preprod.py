from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config.settings import get_settings
from .db import (
    SessionLocal,
    verify_database_migration_head,
)
from .fixtures.canonical import (
    CANONICAL_APPLICATION_IDS,
    CANONICAL_FIXTURE_MANIFEST,
    CANONICAL_PROJECT_IDS,
    synthetic_workspace_root,
)
from .models import (
    ConsultancyOffice,
    PermitApplication,
    Project,
    User,
)
from .seed import cli as seed_cli


EXPECTED_OFFICE_CODE = "QEC-DOHA"

EXPECTED_USER_EMAILS = frozenset(
    CANONICAL_FIXTURE_MANIFEST["users"]
)

EXPECTED_PROJECT_NUMBERS = frozenset(
    CANONICAL_PROJECT_IDS
)

EXPECTED_APPLICATION_NUMBERS = frozenset(
    CANONICAL_APPLICATION_IDS
)


@dataclass(frozen=True)
class BootstrapAnchors:
    office_present: bool
    users: frozenset[str]
    projects: frozenset[str]
    applications: frozenset[str]

    @property
    def complete(self) -> bool:
        return (
            self.office_present
            and self.users
            == EXPECTED_USER_EMAILS
            and self.projects
            == EXPECTED_PROJECT_NUMBERS
            and self.applications
            == EXPECTED_APPLICATION_NUMBERS
        )

    @property
    def any_present(self) -> bool:
        return (
            self.office_present
            or bool(self.users)
            or bool(self.projects)
            or bool(self.applications)
        )


def _bootstrap_anchors(
    db: Session,
) -> BootstrapAnchors:
    office_present = (
        db.scalar(
            select(
                ConsultancyOffice.id
            ).where(
                ConsultancyOffice.office_code
                == EXPECTED_OFFICE_CODE
            )
        )
        is not None
    )

    users = frozenset(
        db.scalars(
            select(User.email).where(
                User.email.in_(
                    EXPECTED_USER_EMAILS
                )
            )
        ).all()
    )

    projects = frozenset(
        db.scalars(
            select(
                Project.project_number
            ).where(
                Project.project_number.in_(
                    EXPECTED_PROJECT_NUMBERS
                )
            )
        ).all()
    )

    applications = frozenset(
        db.scalars(
            select(
                PermitApplication
                .external_request_number
            ).where(
                PermitApplication
                .external_request_number.in_(
                    EXPECTED_APPLICATION_NUMBERS
                )
            )
        ).all()
    )

    return BootstrapAnchors(
        office_present=office_present,
        users=users,
        projects=projects,
        applications=applications,
    )


def _repair_idempotent_post_seed_state() -> None:
    seed_cli.create_fixtures(
        synthetic_workspace_root(),
        clean=False,
    )

    seed_cli.ensure_primary_proposal_sources()

    seed_cli.ensure_proposals_contracts_demo_state()

    seed_cli.ensure_contract_center_golden_state()


def run_preprod_bootstrap() -> str:
    settings = get_settings()

    if settings.app_env.upper() != (
        "AZURE-PREPROD"
    ):
        raise RuntimeError(
            "The synthetic bootstrap is "
            "restricted to AZURE-PREPROD."
        )

    if not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD bootstrap requires "
            "SYNTHETIC_ONLY=true."
        )

    if settings.real_data_allowed:
        raise RuntimeError(
            "AZURE-PREPROD bootstrap requires "
            "REAL_DATA_ALLOWED=false."
        )

    if settings.storage_provider.lower() != "mock":
        raise RuntimeError(
            "AZURE-PREPROD bootstrap requires "
            "STORAGE_PROVIDER=mock."
        )

    if settings.synology_mode.upper() != "SYNTHETIC":
        raise RuntimeError(
            "AZURE-PREPROD bootstrap requires "
            "SYNOLOGY_MODE=SYNTHETIC."
        )

    verify_database_migration_head()

    with SessionLocal() as db:
        anchors = _bootstrap_anchors(db)

        if anchors.complete:
            status = "ALREADY_BOOTSTRAPPED"

        elif anchors.any_present:
            raise RuntimeError(
                "Synthetic bootstrap anchors are "
                "partial or inconsistent; refusing "
                "to overwrite existing data."
            )

        else:
            seed_cli.validate_preprod_migration_baseline(db)
            status = "BOOTSTRAPPED"

    if status == "BOOTSTRAPPED":
        seed_cli.seed(
            initialize_schema=False,
            reset_existing=False,
            clean_fixtures=False,
        )
    else:
        _repair_idempotent_post_seed_state()

    with SessionLocal() as db:
        final_anchors = (
            _bootstrap_anchors(db)
        )

    if not final_anchors.complete:
        raise RuntimeError(
            "Synthetic bootstrap did not produce "
            "the required canonical anchors."
        )

    return status


def main() -> int:
    try:
        status = run_preprod_bootstrap()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": (
                        "proposalops_preprod_bootstrap"
                    ),
                    "status": "FAILED",
                    "error_class": (
                        type(exc).__name__
                    ),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "event": (
                    "proposalops_preprod_bootstrap"
                ),
                "status": status,
                "fixture": (
                    CANONICAL_FIXTURE_MANIFEST[
                        "fixture_set_id"
                    ]
                ),
                "fixture_version": (
                    CANONICAL_FIXTURE_MANIFEST[
                        "semantic_version"
                    ]
                ),
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
