# ProposalOps / AMEC — DSM Operator Package Final 100-Check Validation

```text
RESULT=PASS
CHECKS_TOTAL=100
CHECKS_PASS=100
CHECKS_FAIL=0
OPERATOR_PACKAGE_SHA256=dd03b5e6a0e0ee13c94297e6b6c972b87b0784928fcc8ffd072c1fd5c23a26be
OPERATOR_SCRIPT_SHA256=d19e3708eeec9227384589e37c68b3eb74a7be1909de5261792790dba7e45f6e
LEDGER_SHA256=89230ba979c24101231aae8cb667cc2664551ec50f59cfd7ca5f721a3821128a
NAS_CONNECTION_ATTEMPTS=0
REAL_NAS_ACCESSED=false
REAL_AMEC_READS=0
```

| # | Status | Check | Evidence |
|---:|:---:|---|---|
| 1 | **PASS** | Exact handoff source SHA | 203153beead97910785a4539924bb6b715373466dadec66414a03f68fa7e0172 |
| 2 | **PASS** | Exact handoff source size | 92417319 |
| 3 | **PASS** | Exact handoff source members | 156 |
| 4 | **PASS** | Source handoff has no links | 0 |
| 5 | **PASS** | Operator package exists | /mnt/data/ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL.tar.gz |
| 6 | **PASS** | Operator package has four files | 4 |
| 7 | **PASS** | Operator package single root | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL'] |
| 8 | **PASS** | Operator package no traversal | [] |
| 9 | **PASS** | Operator package no links | [] |
| 10 | **PASS** | Operator package no duplicate names | [] |
| 11 | **PASS** | Package includes operator script | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/OPERATOR_RUN_INSTRUCTIONS.md', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/operator_package_manifest.json', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/proposalops_stage1r_a_production_operator.sh', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/stage1r_a_handoff_file_ledger.tsv'] |
| 12 | **PASS** | Package includes instructions | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/OPERATOR_RUN_INSTRUCTIONS.md', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/operator_package_manifest.json', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/proposalops_stage1r_a_production_operator.sh', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/stage1r_a_handoff_file_ledger.tsv'] |
| 13 | **PASS** | Package includes ledger | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/OPERATOR_RUN_INSTRUCTIONS.md', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/operator_package_manifest.json', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/proposalops_stage1r_a_production_operator.sh', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/stage1r_a_handoff_file_ledger.tsv'] |
| 14 | **PASS** | Package includes package manifest | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/OPERATOR_RUN_INSTRUCTIONS.md', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/operator_package_manifest.json', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/proposalops_stage1r_a_production_operator.sh', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/stage1r_a_handoff_file_ledger.tsv'] |
| 15 | **PASS** | Package excludes handoff/secret | ['ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/OPERATOR_RUN_INSTRUCTIONS.md', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/operator_package_manifest.json', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/proposalops_stage1r_a_production_operator.sh', 'ProposalOps_Stage1R_A_DSM_Operator_Package_FINAL/stage1r_a_handoff_file_ledger.tsv'] |
| 16 | **PASS** | Ledger row count | 156 |
| 17 | **PASS** | Ledger paths unique | 156 |
| 18 | **PASS** | Ledger paths sorted | sorted |
| 19 | **PASS** | Ledger exact path set equals tar | 0 |
| 20 | **PASS** | Ledger all SHA values exact | 156/156 |
| 21 | **PASS** | Ledger all mode values exact | 156/156 |
| 22 | **PASS** | Ledger all size values exact | 156/156 |
| 23 | **PASS** | Ledger no absolute path | 0 |
| 24 | **PASS** | Ledger no traversal | 0 |
| 25 | **PASS** | Ledger no @eaDir | 0 |
| 26 | **PASS** | Ledger SHA pinned in script | 89230ba979c24101231aae8cb667cc2664551ec50f59cfd7ca5f721a3821128a |
| 27 | **PASS** | Ledger SHA recorded in manifest | 89230ba979c24101231aae8cb667cc2664551ec50f59cfd7ca5f721a3821128a |
| 28 | **PASS** | Ledger size recorded in manifest | 21509 |
| 29 | **PASS** | Ledger excludes secret | 0 |
| 30 | **PASS** | Ledger uses relative paths | relative |
| 31 | **PASS** | POSIX sh shebang | #!/bin/sh |
| 32 | **PASS** | dash syntax PASS |  |
| 33 | **PASS** | BusyBox sh syntax PASS |  |
| 34 | **PASS** | Script mode 0755 | 0o755 |
| 35 | **PASS** | set -eu | present |
| 36 | **PASS** | umask 077 | present |
| 37 | **PASS** | No bash shebang | none |
| 38 | **PASS** | No arrays/PIPESTATUS | none |
| 39 | **PASS** | No curl/wget | none |
| 40 | **PASS** | No package installation | none |
| 41 | **PASS** | Control root exact | exact |
| 42 | **PASS** | Canonical staged base exact | exact |
| 43 | **PASS** | Archive root exact | exact |
| 44 | **PASS** | Root user gate | present |
| 45 | **PASS** | Linux gate | present |
| 46 | **PASS** | AMEC hostname gate | present |
| 47 | **PASS** | DS220+ model gate | present |
| 48 | **PASS** | No SSH | none |
| 49 | **PASS** | No SCP | none |
| 50 | **PASS** | No DSM API/QuickConnect | none |
| 51 | **PASS** | No network scan utilities | none |
| 52 | **PASS** | Only control-root /volume1 paths | control-only |
| 53 | **PASS** | Handoff SHA pinned | exact |
| 54 | **PASS** | Handoff size pinned | exact |
| 55 | **PASS** | Handoff members pinned | exact |
| 56 | **PASS** | Handoff content root pinned | exact |
| 57 | **PASS** | Owner attestation SHA pinned | exact |
| 58 | **PASS** | Hash checked before extract | present |
| 59 | **PASS** | Member count checked before extract | present |
| 60 | **PASS** | Staged root symlink rejected | present |
| 61 | **PASS** | 156 regular staged files required | present |
| 62 | **PASS** | 0 staged symlinks required | present |
| 63 | **PASS** | Per-file SHA/mode/size checks | present |
| 64 | **PASS** | Existing differing BASE not overwritten | present |
| 65 | **PASS** | Python 3.8 exact gate | present |
| 66 | **PASS** | Docker gate | present |
| 67 | **PASS** | Frozen runtime path | present |
| 68 | **PASS** | Frozen document runtime | present |
| 69 | **PASS** | Frozen scope | present |
| 70 | **PASS** | Frozen validate_chain invoked | present |
| 71 | **PASS** | Live authority window invoked | present |
| 72 | **PASS** | Attestation/freeze passed to chain | present |
| 73 | **PASS** | Optional exact post_pack only if dependency exists | present |
| 74 | **PASS** | No jsonschema dependency bundled | none |
| 75 | **PASS** | No runtime bundle generated | none |
| 76 | **PASS** | No certification bundle generated | none |
| 77 | **PASS** | No V6.5 | none |
| 78 | **PASS** | Secret path exact | exact |
| 79 | **PASS** | Secret regular/no-symlink gate | present |
| 80 | **PASS** | Secret mode 600 gate | present |
| 81 | **PASS** | Secret nonempty gate | present |
| 82 | **PASS** | Secret never hashed | absent |
| 83 | **PASS** | Secret never catted | absent |
| 84 | **PASS** | Secret never copied | absent |
| 85 | **PASS** | No business-share chmod/chown | none |
| 86 | **PASS** | Wrapper exact --new-run | exact |
| 87 | **PASS** | No direct run_owner command | none |
| 88 | **PASS** | No resume invocation | none |
| 89 | **PASS** | No direct SMB client command | none |
| 90 | **PASS** | No direct business filesystem paths | none |
| 91 | **PASS** | Terminal state exact | exact |
| 92 | **PASS** | all_273 false checked | present |
| 93 | **PASS** | 7/7 preflight checked | present |
| 94 | **PASS** | 273 open ceiling checked | present |
| 95 | **PASS** | 940387450 byte ceiling checked | present |
| 96 | **PASS** | Return archive hygiene outputs | present |
| 97 | **PASS** | Human review required | present |
| 98 | **PASS** | Fallback unauthorized | present |
| 99 | **PASS** | Instructions exact Task Scheduler command | exact |
| 100 | **PASS** | Manifest hashes all three operator files | 3/3 |
