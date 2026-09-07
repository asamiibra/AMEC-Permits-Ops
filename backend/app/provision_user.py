from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .config.settings import get_settings
from .db import (
    SessionLocal,
    verify_database_migration_head,
)
from .models import User


@dataclass(frozen=True)
class ProvisioningResult:
    status: str
    user_id: str
    role: str
    entra_object_id: str


def _canonical_oid(
    value: str,
) -> str:
    try:
        return str(
            UUID(value)
        )
    except (
        ValueError,
        AttributeError,
        TypeError,
    ) as exc:
        raise ValueError(
            "ENTRA object ID must be "
            "a valid GUID."
        ) from exc


def _user_selector_statement(
    *,
    user_id: str | None,
    app_user_email: str | None,
):
    statement = select(User)

    if user_id:
        statement = statement.where(
            User.id == user_id
        )
    else:
        statement = statement.where(
            User.email == app_user_email
        )

    # Lock the selected ProposalOps user so two concurrent
    # provisioning commands cannot silently replace the
    # same user's Entra binding.
    return statement.with_for_update()


def provision_user(
    *,
    entra_object_id: str,
    user_id: str | None = None,
    app_user_email: str | None = None,
) -> ProvisioningResult:
    settings = get_settings()

    if settings.app_env.upper() != (
        "AZURE-PREPROD"
    ):
        raise RuntimeError(
            "Entra user provisioning is "
            "restricted to AZURE-PREPROD."
        )

    if not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD user provisioning "
            "requires SYNTHETIC_ONLY=true."
        )

    if settings.real_data_allowed:
        raise RuntimeError(
            "AZURE-PREPROD user provisioning "
            "requires REAL_DATA_ALLOWED=false."
        )

    if bool(user_id) == bool(
        app_user_email
    ):
        raise ValueError(
            "Specify exactly one ProposalOps "
            "user selector: user_id or "
            "app_user_email."
        )

    object_id = _canonical_oid(
        entra_object_id
    )

    verify_database_migration_head()

    with SessionLocal() as db:
        user = db.scalar(
            _user_selector_statement(
                user_id=user_id,
                app_user_email=app_user_email,
            )
        )

        if user is None:
            raise RuntimeError(
                "ProposalOps user was "
                "not found."
            )

        if not user.active:
            raise RuntimeError(
                "Cannot bind an inactive "
                "ProposalOps user."
            )

        # Lock an existing owner where one already exists.
        # The unique DB index remains the final protection
        # against two simultaneous first-time OID claims.
        existing_owner = db.scalar(
            select(User)
            .where(
                User.entra_object_id
                == object_id
            )
            .with_for_update()
        )

        if (
            existing_owner is not None
            and existing_owner.id
            != user.id
        ):
            raise RuntimeError(
                "The Entra object ID is "
                "already bound to another "
                "ProposalOps user."
            )

        if user.entra_object_id:
            if (
                _canonical_oid(
                    user.entra_object_id
                )
                != object_id
            ):
                raise RuntimeError(
                    "ProposalOps user is "
                    "already bound to a "
                    "different Entra object ID."
                )

            return ProvisioningResult(
                status="ALREADY_BOUND",
                user_id=user.id,
                role=user.role.value,
                entra_object_id=object_id,
            )

        user.entra_object_id = object_id

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()

            raise RuntimeError(
                "The Entra object ID could not "
                "be bound because the identity "
                "binding changed concurrently or "
                "is already owned."
            ) from exc

        return ProvisioningResult(
            status="BOUND",
            user_id=user.id,
            role=user.role.value,
            entra_object_id=object_id,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bind one existing synthetic "
            "ProposalOps user to an explicit "
            "Microsoft Entra object ID."
        )
    )

    parser.add_argument(
        "--entra-object-id",
        required=True,
    )

    selector = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    selector.add_argument(
        "--user-id",
    )

    selector.add_argument(
        "--app-user-email",
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(
        argv
    )

    try:
        result = provision_user(
            entra_object_id=(
                args.entra_object_id
            ),
            user_id=args.user_id,
            app_user_email=(
                args.app_user_email
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": (
                        "proposalops_user_provision"
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
                    "proposalops_user_provision"
                ),
                "status": result.status,
                "user_id": result.user_id,
                "role": result.role,
                "entra_object_id": (
                    result.entra_object_id
                ),
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
