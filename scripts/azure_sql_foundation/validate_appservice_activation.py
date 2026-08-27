#!/usr/bin/env python3
"""Semantic, standard-library-only validation for the R2R3 App Service plan lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


BASE_SHA = "ce8a887703ec8c15c8c781e1589e169ce395845a"
EXPECTED_APP_SHA = "4925518b35b58956aaa5870f226af5e57d14b610"
EXPECTED_APP_TREE = "9dafcf25ac59d4dc2940c03bb081206d7f2820fa"
EXPECTED_PLAN_ID = "/subscriptions/2bea2887-9255-4273-a73f-43ae33813455/resourceGroups/rg-proposalops-prod-qc/providers/Microsoft.Web/serverfarms/asp-proposalops-prod-qc"
EXPECTED_PATHS = {
    "infra/azure_sql_foundation/main.bicep",
    "infra/azure_sql_foundation/modules/core.bicep",
    "infra/azure_sql_foundation/modules/app_service_plan.bicep",
    "infra/azure_sql_foundation/foundation.bicepparam.example",
    "scripts/azure_sql_foundation/validate_appservice_activation.py",
}
PRESERVED_BLOBS = {
    "infra/azure_sql_foundation/modules/network.bicep": "ade5b3bd32692bcace520fb5eba072a19ed363ce",
    "infra/azure_sql_foundation/modules/private_dns.bicep": "01db763d8827359b98ab80ba7e5f42717f16079e",
    "infra/azure_sql_foundation/modules/budget.bicep": "94a15b2bee1b0838e5453eca7eca1941eb2a5ac5",
    "scripts/azure_sql_foundation/validate_foundation.sh": "302984d249229858b593226c8ea6b785c653ad8d",
    ".github/workflows/azure-sql-foundation-static.yml": "a741f1fb106cbff3b4f6694de40b11a3d4b43c33",
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def git_raw(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.rstrip("\n")


def git_succeeds(root: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def bicep_build(root: Path, source: Path) -> dict:
    result = subprocess.run(
        ["az", "bicep", "build", "--file", str(source), "--stdout"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(result.stdout)


def recursive_resources(template: dict) -> list[dict]:
    found: list[dict] = []
    for resource in template.get("resources", []):
        found.append(resource)
        properties = resource.get("properties")
        if isinstance(properties, dict) and isinstance(properties.get("template"), dict):
            found.extend(recursive_resources(properties["template"]))
    return found


def normalize_type(value: str) -> str:
    return value.split("@", 1)[0].lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-sha", default=BASE_SHA)
    parser.add_argument("--candidate-sha")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--compiled-out-dir", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    checks: list[dict] = []
    failures: list[dict] = []

    def check(category: str, name: str, condition: bool, detail: str = "") -> None:
        record = {"category": category, "name": name, "result": "PASS" if condition else "FAIL"}
        if detail:
            record["detail"] = detail
        checks.append(record)
        if not condition:
            failures.append(record)

    files = {
        "main": root / "infra/azure_sql_foundation/main.bicep",
        "core": root / "infra/azure_sql_foundation/modules/core.bicep",
        "plan": root / "infra/azure_sql_foundation/modules/app_service_plan.bicep",
        "params": root / "infra/azure_sql_foundation/foundation.bicepparam.example",
        "network": root / "infra/azure_sql_foundation/modules/network.bicep",
        "dns": root / "infra/azure_sql_foundation/modules/private_dns.bicep",
    }
    for key, path in files.items():
        check("SOURCE_SCOPE", f"{key}_exists", path.is_file(), str(path))
    if not all(path.is_file() for path in files.values()):
        return finish(root, checks, failures, args.json_out)

    head = git(root, "rev-parse", "HEAD")
    base = args.base_sha
    check("SOURCE_SCOPE", "base_commit_exists", git_succeeds(root, "cat-file", "-e", f"{base}^{{commit}}"))
    check("SOURCE_SCOPE", "head_is_base_or_direct_child", head == base or git(root, "rev-parse", "HEAD^") == base, head)
    if args.candidate_sha:
        check("SOURCE_SCOPE", "candidate_head_exact", head == args.candidate_sha, head)
        check("SOURCE_SCOPE", "candidate_parent_exact", git(root, "rev-parse", "HEAD^") == base)
        changed = set(git(root, "diff", "--name-only", base, head).splitlines())
    elif head == base:
        status_lines = git_raw(root, "status", "--porcelain=v1").splitlines()
        changed = {line[3:] for line in status_lines if len(line) >= 4}
    else:
        changed = set(git(root, "diff", "--name-only", base, head).splitlines())
    check("SOURCE_SCOPE", "exact_five_path_boundary", changed == EXPECTED_PATHS, repr(sorted(changed)))
    check("SOURCE_SCOPE", "no_unexpected_product_changes", not (changed - EXPECTED_PATHS), repr(sorted(changed - EXPECTED_PATHS)))

    for path, expected in PRESERVED_BLOBS.items():
        actual = git(root, "hash-object", path)
        check("R2R2_PRESERVATION", f"preserved_{Path(path).name}_blob", actual == expected, f"{actual} != {expected}")
    check("R2R2_PRESERVATION", "accepted_application_tree", git(root, "rev-parse", f"{EXPECTED_APP_SHA}^{{tree}}") == EXPECTED_APP_TREE)

    main_text = files["main"].read_text()
    core_text = files["core"].read_text()
    plan_text = files["plan"].read_text()
    params_text = files["params"].read_text()
    executable_successor_text = {
        "main": main_text,
        "core": core_text,
        "plan": plan_text,
        "params": params_text,
    }

    check("B1_REMOVAL", "no_forbidden_B1_successor_literal", all("B1" not in value for value in executable_successor_text.values()))
    check("B1_REMOVAL", "core_has_no_plan_resource", "Microsoft.Web/serverfarms" not in core_text)
    check("B1_REMOVAL", "core_has_no_plan_outputs", "outputs" not in core_text or "planName" not in core_text)

    sku_allowed = re.search(r"@allowed\(\[\s*'B2'\s*'B3'\s*\]\)\s*@description\([^)]*\)\s*param appServicePlanSku", main_text, re.S)
    module_sku_allowed = re.search(r"@allowed\(\[\s*'B2'\s*'B3'\s*\]\)\s*param skuName", plan_text, re.S)
    check("SKU_CONTRACT", "main_exact_B2_B3_allowlist", bool(sku_allowed))
    check("SKU_CONTRACT", "module_exact_B2_B3_allowlist", bool(module_sku_allowed))
    check("SKU_CONTRACT", "no_forbidden_sku_terms", not re.search(r"\b(?:B1|B4|Standard|Premium)\b", main_text + core_text + plan_text + params_text))
    check("SKU_CONTRACT", "example_preferred_sku_is_B2", "param appServicePlanSku = 'B2'" in params_text)
    check("SAFE_DEFAULT", "deployment_default_false", "param deployAppServicePlan bool = false" in main_text)
    check("SAFE_DEFAULT", "activation_requires_explicit_sku", "param appServicePlanSku string" in main_text)

    check("PLAN_CONTRACT", "one_serverfarm_resource", len(re.findall(r"^resource\s+\w+\s+'Microsoft\.Web/serverfarms@2024-04-01'", plan_text, re.M)) == 1)
    for required in ("kind: 'linux'", "tier: 'Basic'", "size: skuName", "family: 'B'", "capacity: 1", "reserved: true"):
        check("PLAN_CONTRACT", f"plan_has_{required}", required in plan_text)
    check("PLAN_CONTRACT", "plan_module_target_resource_group", "targetScope = 'resourceGroup'" in plan_text)
    check("PLAN_CONTRACT", "no_forbidden_plan_resources", not re.search(r"Microsoft\.(?:Web/sites|Network/privateEndpoints|Network/privateDnsZones|Sql/|DBforPostgreSQL/|DBforMySQL/|DocumentDB/|KeyVault/|ContainerRegistry/|ManagedIdentity/)", plan_text, re.I))
    check("PLAN_CONTRACT", "no_zone_redundancy_or_autoscale", not re.search(r"zoneRedundant|autoscale", plan_text, re.I))
    check("PLAN_CONTRACT", "plan_outputs_present", "output planName string" in plan_text and "output planId string" in plan_text)

    check("PROVENANCE_CONTRACT", "main_preserves_foundation_tag", "foundationSourceSha: foundationSourceSha" in main_text)
    check("PROVENANCE_CONTRACT", "main_declares_activation_sha", "param appServiceActivationSourceSha string" in main_text)
    check("PROVENANCE_CONTRACT", "activation_sha_length_bounds", "@minLength(40)" in main_text and "@maxLength(40)" in main_text)
    check("PROVENANCE_CONTRACT", "plan_has_both_provenance_tags", "foundationSourceSha: foundationSourceSha" in plan_text and "appServiceActivationSourceSha: appServiceActivationSourceSha" in plan_text)
    check("PROVENANCE_CONTRACT", "activation_revision_tag", "appServiceActivationRevision: 'R2R3-B2B3-v1'" in plan_text)
    check("PROVENANCE_CONTRACT", "core_receives_no_activation_sha", "appServiceActivationSourceSha" not in core_text)
    check("PROVENANCE_CONTRACT", "main_passes_activation_sha_only_to_plan", "appServiceActivationSourceSha: appServiceActivationSourceSha" in main_text)
    check("PROVENANCE_CONTRACT", "real_data_false", "realDataAllowed: 'false'" in main_text and "realDataAllowed: 'false'" in plan_text)

    check("NETWORK_PRESERVATION", "vnet_cidr_preserved", "10.42.0.0/16" in files["network"].read_text())
    check("NETWORK_PRESERVATION", "appservice_subnet_preserved", "10.42.0.0/26" in files["network"].read_text())
    check("NETWORK_PRESERVATION", "sql_pe_subnet_preserved", "10.42.1.0/28" in files["network"].read_text())
    check("NETWORK_PRESERVATION", "web_delegation_preserved", "Microsoft.Web/serverFarms" in files["network"].read_text())
    dns_text = files["dns"].read_text()
    check("DNS_PRESERVATION", "dns_global_zone", "location: 'global'" in dns_text)
    check("DNS_PRESERVATION", "dns_link_global", "location: 'global'" in dns_text)
    check("DNS_PRESERVATION", "dns_registration_disabled", "registrationEnabled: false" in dns_text)

    secret_pattern = re.compile(r"BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|Bearer\s|clientSecret|accessToken|refreshToken|password\s*=|secret\s*=", re.I)
    scan_text = "\n".join(path.read_text() for path in (files["main"], files["core"], files["plan"], files["params"]))
    check("SECRETS", "no_secret_shaped_source_values", not secret_pattern.search(scan_text))

    compiled: dict[str, dict] = {}
    compile_failed = False
    with tempfile.TemporaryDirectory(prefix="amec-appservice-bicep-") as temp_dir:
        for key in ("main", "plan"):
            try:
                compiled[key] = bicep_build(root, files[key])
                if args.compiled_out_dir:
                    args.compiled_out_dir.mkdir(parents=True, exist_ok=True)
                    (args.compiled_out_dir / f"compiled_{'main' if key == 'main' else 'app_service_plan'}.json").write_text(
                        json.dumps(compiled[key], indent=2, sort_keys=True) + "\n"
                    )
                check("BICEP_BUILD", f"{key}_build", True)
            except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                compile_failed = True
                check("BICEP_BUILD", f"{key}_build", False, str(exc))
    if not compile_failed:
        main_arm = compiled["main"]
        plan_arm = compiled["plan"]
        plan_resources = [r for r in recursive_resources(plan_arm) if normalize_type(r.get("type", "")) == "microsoft.web/serverfarms"]
        check("BICEP_BUILD", "compiled_main_has_one_serverfarm", len(plan_resources) == 1)
        check("BICEP_BUILD", "compiled_plan_has_one_serverfarm", len([r for r in recursive_resources(plan_arm) if normalize_type(r.get("type", "")) == "microsoft.web/serverfarms"]) == 1)
        direct_plan_resources = [r for r in plan_arm.get("resources", []) if normalize_type(r.get("type", "")) == "microsoft.web/serverfarms"]
        check("BICEP_BUILD", "compiled_plan_module_has_one_direct_serverfarm", len(direct_plan_resources) == 1)
        if direct_plan_resources:
            resource = direct_plan_resources[0]
            check("PLAN_CONTRACT", "compiled_plan_api_version", resource.get("apiVersion") == "2024-04-01")
            check("PLAN_CONTRACT", "compiled_plan_kind_linux", resource.get("kind") == "linux")
            check("PLAN_CONTRACT", "compiled_plan_basic", resource.get("sku", {}).get("tier") == "Basic")
            check("PLAN_CONTRACT", "compiled_plan_family_B", resource.get("sku", {}).get("family") == "B")
            check("PLAN_CONTRACT", "compiled_plan_capacity_one", resource.get("sku", {}).get("capacity") == 1)
            check("PLAN_CONTRACT", "compiled_plan_reserved", resource.get("properties", {}).get("reserved") is True)
            check("PLAN_CONTRACT", "compiled_plan_tags_reference", resource.get("tags") == "[variables('planTags')]")
            compiled_tags = plan_arm.get("variables", {}).get("planTags", {})
            check("PLAN_CONTRACT", "compiled_plan_provenance_tags", "appServiceActivationSourceSha" in compiled_tags)
        params = main_arm.get("parameters", {})
        check("BICEP_BUILD", "compiled_main_safe_default_false", params.get("deployAppServicePlan", {}).get("defaultValue") is False)
        check("BICEP_BUILD", "compiled_main_sku_allowlist", params.get("appServicePlanSku", {}).get("allowedValues") == ["B2", "B3"])
        check("BICEP_BUILD", "compiled_main_activation_sha_parameter", "appServiceActivationSourceSha" in params)

    category_results = {}
    for record in checks:
        category_results.setdefault(record["category"], []).append(record)
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "base_sha": base,
        "head_sha": head,
        "checks": len(checks),
        "failures": len(failures),
        "categories": {
            category: {
                "checks": len(records),
                "failures": sum(record["result"] == "FAIL" for record in records),
                "result": "PASS" if all(record["result"] == "PASS" for record in records) else "FAIL",
            }
            for category, records in category_results.items()
        },
        "failed_checks": failures,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return finish(root, checks, failures, args.json_out, summary)


def finish(root: Path, checks: list[dict], failures: list[dict], json_out: Path | None, summary: dict | None = None) -> int:
    categories = {}
    for record in checks:
        categories.setdefault(record["category"], []).append(record)
    print("APP_SERVICE_ACTIVATION_LOCAL_VALIDATION=" + ("PASS" if not failures else "FAIL"))
    print(f"CHECKS={len(checks)}")
    print(f"FAILURES={len(failures)}")
    for category in ("SOURCE_SCOPE", "R2R2_PRESERVATION", "B1_REMOVAL", "SKU_CONTRACT", "SAFE_DEFAULT", "PLAN_CONTRACT", "PROVENANCE_CONTRACT", "NETWORK_PRESERVATION", "DNS_PRESERVATION", "BICEP_BUILD", "SECRETS"):
        records = categories.get(category, [])
        print(f"{category}=" + ("PASS" if records and all(record["result"] == "PASS" for record in records) else "FAIL"))
    if failures:
        for record in failures:
            print("FAILURE=" + record["category"] + ":" + record["name"] + (":" + record.get("detail", "") if record.get("detail") else ""))
    if summary is not None and json_out:
        print(f"JSON_SUMMARY={json_out}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
