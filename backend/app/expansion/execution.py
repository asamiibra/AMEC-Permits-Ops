"""Prototype-only execution authority and shared expansion safety policy."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import HTTPException


class ExecutionAuthority(str, Enum):
    PROTOTYPE_DEV_ONLY = "PROTOTYPE_DEV_ONLY"
    FORMAL_BUILD_AUTHORIZED = "FORMAL_BUILD_AUTHORIZED"
    PRODUCTION_AUTHORIZED = "PRODUCTION_AUTHORIZED"


class EvidenceClass(str, Enum):
    SYNTHETIC_IMPLEMENTATION_EVIDENCE = "SYNTHETIC_IMPLEMENTATION_EVIDENCE"
    APPROVED_TEST_EVIDENCE = "APPROVED_TEST_EVIDENCE"
    CLIENT_VALIDATED_EVIDENCE = "CLIENT_VALIDATED_EVIDENCE"
    LIVE_PRODUCTION_EVIDENCE = "LIVE_PRODUCTION_EVIDENCE"


@dataclass(frozen=True)
class ExecutionPolicy:
    authority: ExecutionAuthority = ExecutionAuthority.PROTOTYPE_DEV_ONLY
    evidence_class: EvidenceClass = EvidenceClass.SYNTHETIC_IMPLEMENTATION_EVIDENCE
    production_enabled: bool = False
    real_email_send: bool = False
    real_accounting_write: bool = False
    real_portal_write: bool = False
    production_template_release: bool = False
    real_engineering_authority_claim: bool = False
    government_submit: bool = False

    @property
    def policy_classes(self) -> dict[str, dict[str, Any]]:
        return {
            "INTERNAL_READ": {"allowed": True, "human_review": False},
            "INTERNAL_DRAFT": {"allowed": True, "human_review": True},
            "HUMAN_APPROVAL_REQUIRED": {"allowed": True, "human_review": True},
            "EXTERNAL_DRAFT": {"allowed": True, "human_review": True},
            "EXTERNAL_HUMAN_SEND": {"allowed": False, "human_review": True, "reason": "HUMAN_SEND_ONLY"},
            "EXTERNAL_AUTOMATED_WRITE": {"allowed": False, "reason": "EXTERNAL_ACTION_DISABLED"},
            "PROFESSIONAL_DECISION": {"allowed": False, "reason": "AUTHORIZED_HUMAN_REQUIRED"},
            "COMMERCIAL_DECISION": {"allowed": False, "reason": "AUTHORIZED_HUMAN_REQUIRED"},
            "GOVERNMENT_FINAL_SUBMISSION": {"allowed": False, "reason": "HUMAN_SUBMISSION_REQUIRED"},
            "ACCOUNTING_WRITE": {"allowed": False, "reason": "ACCOUNTING_WRITE_DISABLED"},
        }

    def assert_allowed(self, capability: str, environment: str = "DEV", *, external: bool = False) -> None:
        if self.authority == ExecutionAuthority.PROTOTYPE_DEV_ONLY and environment.upper() not in {"DEV", "TEST"}:
            raise HTTPException(status_code=403, detail="PROTOTYPE_DEV_ONLY_ENVIRONMENT_REQUIRED")
        if self.authority != ExecutionAuthority.PRODUCTION_AUTHORIZED and environment.upper() == "PROD":
            raise HTTPException(status_code=403, detail="PRODUCTION_AUTHORIZATION_REQUIRED")
        if external or capability in {"REAL_EMAIL_SEND", "REAL_ACCOUNTING_WRITE", "REAL_PORTAL_WRITE", "GOVERNMENT_SUBMIT"}:
            raise HTTPException(status_code=403, detail=f"EXTERNAL_ACTION_DISABLED:{capability}")


PROTOTYPE_POLICY = ExecutionPolicy()


def policy_snapshot() -> dict[str, Any]:
    return {
        "execution_authority": PROTOTYPE_POLICY.authority.value,
        "evidence_class": PROTOTYPE_POLICY.evidence_class.value,
        "production_enabled": PROTOTYPE_POLICY.production_enabled,
        "external_actions": {
            "real_email_send": PROTOTYPE_POLICY.real_email_send,
            "real_accounting_write": PROTOTYPE_POLICY.real_accounting_write,
            "real_portal_write": PROTOTYPE_POLICY.real_portal_write,
            "production_template_release": PROTOTYPE_POLICY.production_template_release,
            "real_engineering_authority_claim": PROTOTYPE_POLICY.real_engineering_authority_claim,
            "government_submit": PROTOTYPE_POLICY.government_submit,
        },
        "policy_classes": PROTOTYPE_POLICY.policy_classes,
        "no_real_side_effects": True,
    }


def require_human_role(actor_role: str | None, allowed: set[str]) -> str:
    role = (actor_role or "").strip().upper()
    if role not in allowed:
        raise HTTPException(status_code=403, detail={"code": "HUMAN_ROLE_REQUIRED", "allowed_roles": sorted(allowed)})
    return role
