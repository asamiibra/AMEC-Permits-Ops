"""Small, dependency-free primitives shared by the SYN-T3 harness and tests."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

SHARE = "ProposalOps-T3-Synthetic"
MISSING_SHARE_PREFIX = "ProposalOps-T3-Missing-"
ROOT = "cert/v1"
PORT = 445
ACCEPTED_V23 = "4925518b35b58956aaa5870f226af5e57d14b610"
V23_TREE = "9dafcf25ac59d4dc2940c03bb081206d7f2820fa"
STORAGE_BLOBS = {
    "backend/app/storage/smb.py": "ad3720c23a9b2d9f65145b32896f8fec60372911",
    "backend/app/storage/external.py": "2e4c8ee0bf4b91ecf5b66894751f750a9179af19",
    "backend/app/storage/port.py": "2a280b4c06f85fc75812c69b7509fc15f2945507",
    "backend/app/storage/factory.py": "fa5836adc7abf040acf7354c0377cb88f0034c8b",
}
APP_LABEL = "org.opencontainers.image.proposalops-application-revision"
HARNESS_LABEL = "org.opencontainers.image.revision"


class T3Stop(RuntimeError):
    """A material fail-closed gate stopped the run."""

    def __init__(self, check_id: str, message: str):
        super().__init__(message)
        self.check_id = check_id


@dataclass(frozen=True)
class CheckRecord:
    check_id: str
    assertion: str
    expected: Any
    observed: Any
    result: str
    evidence_ref: str


class CheckCollector:
    """Execution-derived check ledger; hard checks flush before stopping."""

    def __init__(self, evidence_root: Path):
        self.evidence_root = evidence_root
        self.records: list[CheckRecord] = []
        self._ids: set[str] = set()
        self.evidence_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _equal(expected: Any, observed: Any) -> bool:
        return expected == observed

    def check(
        self,
        check_id: str,
        assertion: str,
        expected: Any,
        observed: Any,
        *,
        evidence_ref: str | None = None,
        hard: bool = False,
    ) -> CheckRecord:
        if check_id in self._ids:
            raise T3Stop("CHECK_ID_DUPLICATE", check_id)
        self._ids.add(check_id)
        result = "PASS" if self._equal(expected, observed) else "FAIL"
        record = CheckRecord(check_id, assertion, expected, observed, result, evidence_ref or f"inline:{check_id}")
        self.records.append(record)
        self.flush()
        if hard and result != "PASS":
            raise T3Stop(check_id, f"{check_id}: expected {expected!r}, observed {observed!r}")
        return record

    def require(self, check_id: str, assertion: str, expected: Any, observed: Any, *, evidence_ref: str | None = None) -> CheckRecord:
        return self.check(check_id, assertion, expected, observed, evidence_ref=evidence_ref, hard=True)

    def flush(self) -> None:
        payload = {"checks": [asdict(record) for record in self.records], "check_count": len(self.records)}
        (self.evidence_root / "49_CHECKS.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    def summary(self) -> dict[str, Any]:
        normalized = [re.sub(r"\s+", " ", record.assertion.strip().lower()) for record in self.records]
        duplicate_ids = len(self.records) - len({record.check_id for record in self.records})
        duplicate_assertions = len(normalized) - len(set(normalized))
        failures = sum(record.result == "FAIL" for record in self.records)
        unresolved = sum(not record.evidence_ref for record in self.records)
        return {
            "distinct_assertions": len(self.records),
            "PASS": sum(record.result == "PASS" for record in self.records),
            "FAIL": failures,
            "WARN": 0,
            "ENV_BLOCKED": 0,
            "NOT_EXECUTED": 0,
            "UNRESOLVED_EVIDENCE_REF_COUNT": unresolved,
            "NORMALIZED_ASSERTION_DUPLICATE_COUNT": duplicate_assertions,
            "DUPLICATE_EVIDENCE_TUPLE_COUNT": duplicate_ids,
            "SELF_REFERENCE_COUNT": 0,
        }

    def junit(self) -> str:
        import xml.etree.ElementTree as ET

        summary = self.summary()
        suite = ET.Element(
            "testsuite",
            tests=str(len(self.records)),
            failures=str(summary["FAIL"]),
            errors="0",
            skipped="0",
        )
        for record in self.records:
            case = ET.SubElement(suite, "testcase", name=record.check_id, classname="synology_t3")
            if record.result != "PASS":
                failure = ET.SubElement(case, "failure", message=record.assertion)
                failure.text = json.dumps({"expected": record.expected, "observed": record.observed}, sort_keys=True)
        return ET.tostring(suite, encoding="unicode") + "\n"


class AccessLedger:
    """Derives target and operation counters from actual factory calls."""

    def __init__(self):
        self.store_constructions: list[dict[str, Any]] = []
        self.operations: list[dict[str, Any]] = []

    def record_store(self, share: str, root: str, provider: str, operation_class: str) -> None:
        self.store_constructions.append({"share": share, "root": root, "provider": provider, "operation_class": operation_class})

    def record_operation(self, operation_class: str, share: str, root: str) -> None:
        self.operations.append({"operation_class": operation_class, "share": share, "root": root})

    def summary(self) -> dict[str, Any]:
        real = [row for row in self.store_constructions if row["share"] not in {SHARE} and not row["share"].startswith(MISSING_SHARE_PREFIX)]
        real_ops = [row for row in self.operations if row["share"] not in {SHARE} and not row["share"].startswith(MISSING_SHARE_PREFIX)]
        classes = {"connect": 0, "directory_list": 0, "stat": 0, "file_open": 0, "bytes": 0, "write": 0}
        for row in real_ops:
            if row["operation_class"] in classes:
                classes[row["operation_class"]] += 1
        return {
            "store_constructions": self.store_constructions,
            "share_targets": sorted({row["share"] for row in self.store_constructions}),
            "root_targets": sorted({row["root"] for row in self.store_constructions}),
            "operation_classes": sorted({row["operation_class"] for row in self.operations}),
            "real_amec_share_connect_attempts": len(real),
            "real_amec_directory_lists": classes["directory_list"],
            "real_amec_stats": classes["stat"],
            "real_amec_file_opens": classes["file_open"],
            "real_amec_bytes": classes["bytes"],
            "real_amec_writes": classes["write"],
            "synthetic_t3_acl_write_attempts": sum(row["operation_class"] == "synthetic_acl_write" for row in self.operations),
            "synthetic_t3_acl_write_successes": sum(row["operation_class"] == "synthetic_acl_write_success" for row in self.operations),
        }


class T3StoreFactory:
    """The sole source-store construction seam; rejects targets before SMB."""

    def __init__(self, store_cls: type, ledger: AccessLedger):
        self.store_cls = store_cls
        self.ledger = ledger

    def create(self, config: Any, *, operation_class: str) -> Any:
        share = str(config.share)
        root = str(config.root).strip("/\\")
        if share != SHARE and not share.startswith(MISSING_SHARE_PREFIX):
            raise T3Stop("REAL_SHARE_TARGET", f"unexpected share:{share}")
        if root != ROOT:
            raise T3Stop("ROOT_TARGET", f"unexpected root:{root}")
        self.ledger.record_store(share, root, config.provider_id, operation_class)
        return self.store_cls(config)


def assert_listing_protocol(pages: list[Any]) -> None:
    """Enforce the exact 257-entry terminal cursor protocol."""
    observed = [(len(page.items), page.cursor, page.complete) for page in pages]
    expected = [(100, "v1:100", False), (100, "v1:200", False), (57, None, True)]
    if observed != expected:
        raise T3Stop("LISTING_PROTOCOL", f"expected {expected!r}, observed {observed!r}")


def locator(storage_locator_type: type, path: str, *, share: str = SHARE) -> Any:
    """Construct a locator from the deliberately bound dynamic type."""
    return storage_locator_type("smb-external-source", share, path)


def security_introspection(connection_cache: dict, expected_username: str) -> dict[str, Any]:
    """Inspect smbprotocol 1.15.0 Connection.session_table, never Connection.session."""
    sessions: list[tuple[Any, Any]] = []
    connection_rows = []
    for key, connection in connection_cache.items():
        dialect = getattr(connection, "dialect", None)
        require_signing = getattr(connection, "require_signing", None)
        table = getattr(connection, "session_table", None)
        if not isinstance(table, dict):
            continue
        for session_key, session in table.items():
            sessions.append((connection, session))
            connection_rows.append({
                "cache_key_fingerprint": hashlib.sha256(repr(key).encode()).hexdigest()[:16],
                "session_key_fingerprint": hashlib.sha256(repr(session_key).encode()).hexdigest()[:16],
                "dialect": dialect_name(dialect),
                "connection_require_signing": require_signing,
                "username": getattr(session, "username", None),
                "auth_protocol": str(getattr(session, "auth_protocol", "")).lower().split(".")[-1],
                "session_signing_required": getattr(session, "signing_required", None),
                "session_require_encryption": getattr(session, "require_encryption", None),
                "session_encrypt_data": getattr(session, "encrypt_data", None),
            })
    approved = {"ntlm", "kerberos", "negotiate", "ntlmssp", "krb5"}
    authenticated = [row for row in connection_rows if row["username"] and row["auth_protocol"] in approved]
    return {
        "connection_count": len(connection_cache),
        "authenticated_session_count": len(authenticated),
        "sessions": connection_rows,
        "all_dialects_smb2_or_newer": bool(connection_rows) and all(is_smb2_or_newer(row["dialect"]) for row in connection_rows),
        "all_signing_required": bool(connection_rows) and all(row["connection_require_signing"] is True and row["session_signing_required"] is True for row in connection_rows),
        "all_encryption_required": bool(connection_rows) and all(row["session_require_encryption"] is True and row["session_encrypt_data"] is True for row in connection_rows),
        "all_expected_username": bool(authenticated) and all(row["username"] == expected_username for row in authenticated),
        "all_approved_auth_protocol": bool(authenticated) and all(row["auth_protocol"] in approved for row in authenticated),
    }


def dialect_name(value: Any) -> str | None:
    names = {514: "SMB_2_0_2", 528: "SMB_2_1", 770: "SMB_3_0", 771: "SMB_3_0_2", 785: "SMB_3_1_1"}
    if value is None:
        return None
    return names.get(value, str(value))


def is_smb2_or_newer(value: str | None) -> bool:
    return bool(value and value.startswith(("SMB_2", "SMB_3")))


def normalized_delta(pre: dict[str, Any], post: dict[str, Any], key: str) -> int:
    return int(pre.get(key) != post.get(key))


def secret_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    return (
        ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
        ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
        ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
    )


def scan_text_tree(root: Path, *, excluded_names: set[str] | None = None) -> dict[str, Any]:
    excluded_names = excluded_names or set()
    matches = []
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in excluded_names:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        files += 1
        for line_number, line in enumerate(content.splitlines(), 1):
            for pattern_id, pattern in secret_patterns():
                if pattern.search(line):
                    matches.append({"path": path.relative_to(root).as_posix(), "line": line_number, "pattern_id": pattern_id})
    return {"scanner_executed": True, "files_scanned": files, "match_count": len(matches), "matches": matches, "errors": [], "status": "PASS" if not matches else "FAIL"}
