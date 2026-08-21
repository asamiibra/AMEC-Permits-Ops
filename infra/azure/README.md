# ProposalOps Azure A1 Step 3A.4A

This directory is a static, subscription-scope Bicep graph for the Qatar
Central F1 preproduction architecture. It is intentionally foundation-only
by default:

- `deployApps = false`
- `deployPostgres = false`
- `APP_ENV = AZURE-PREPROD`
- `SYNTHETIC_ONLY = true`
- `REAL_DATA_ALLOWED = false`
- `AUTH_MODE = ENTRA`
- `STORAGE_PROVIDER = mock`
- `SYNOLOGY_MODE = SYNTHETIC`

The default parameter file does not contain tenant/client production IDs,
database passwords, Azure secrets, SMB credentials, Synology credentials, or
business data. Future image references and Entra IDs are parameters and must
be supplied only at an independently authorized deployment boundary.

## Graph

The subscription-scope root previews a resource group, Qatar Central VNet,
delegated App Service and PostgreSQL subnets, ACR Basic with admin disabled,
RBAC-enabled Key Vault, Log Analytics, workspace-based Application Insights,
and a Basic B1 Linux App Service Plan. App Service sites and PostgreSQL
Flexible Server 16 are modeled in conditional modules and remain disabled by
the committed preproduction parameters.

No Container Apps, AKS, VM, public IP, VPN gateway, NAT gateway, firewall,
NAS route, cross-region network, or PostgreSQL public access is modeled.

## Runtime contract

When the later application boundary enables the App Service module:

- frontend uses a Linux custom container on port `8080`;
- backend uses a Linux custom container on port `8000`;
- frontend storage is disabled;
- backend `/home` persistence is enabled for the synthetic workspace;
- both sites use system-assigned identity and ACR pull through `AcrPull`;
- backend synthetic/preproduction flags remain fail-closed;
- both sites require HTTPS, TLS 1.2, disabled FTPS, and disabled basic
  publishing credentials;
- backend CORS is the exact planned HTTPS frontend origin, never `*`;
- backend keeps `WEBSITE_SKIP_RUNNING_KUDUAGENT=false` and `alwaysOn=true`.

The backend image already defines these commands:

```text
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
python -m backend.app.migrate
python -m backend.app.bootstrap_preprod
python -m backend.app.provision_user ...
python -m backend.app.worker
```

`WEBJOB_DISCOVERY_VERIFIED=false` and `WEBJOB_DEPLOYED=false`. A bounded
worker command is documented for a later triggered/scheduled WebJob proof;
this static IaC step does not fabricate or deploy a WebJob resource.

Application Insights and Log Analytics resources model monitoring targets;
their presence does not prove that application telemetry is flowing. When
`deployApps=true`, App Service diagnostic settings route platform logs and
metrics to Log Analytics. Python container application telemetry remains a
later code-based OpenTelemetry hardening task.

`APP_SERVICE_HEALTH_CHECK = DEFERRED_UNTIL_TRUE_READINESS_ENDPOINT`.
App Service Health Check is intentionally not configured for `/health` until
the application exposes a readiness endpoint that returns `503` for critical
database or migration failures.

The B1 / Basic plan is capacity `1` and has no deployment slots in this
design. PostgreSQL is modeled as Flexible Server 16 with private DNS, a
private delegated subnet, an explicit backup-retention parameter, and the
`proposalops` application database child resource; `deployPostgres=false`
keeps it out of the default deployment.

All modeled resources use deterministic non-personal tags:
`application=ProposalOps`, `environment=preprod`,
`dataMode=synthetic-only`, `regionIntent=qatarcentral`, and `managedBy=bicep`.
No forced all-route VNet behavior or Azure-to-Synology route is modeled, so
public Microsoft identity/control-plane dependencies remain reachable.

## Read-only what-if

`scripts/azure/step3a4_whatif.sh` is the future Step 3A.4B execution surface.
It binds every applicable Azure command to the ProposalOps Preprod QC
subscription and performs only account/provider reads and subscription-scope
ARM what-if operations. It never logs in, registers providers, deploys, or
mutates resources.
