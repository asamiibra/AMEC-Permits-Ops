# ProposalOps Azure A1 — F1 App Service Implementation Appendix

**Status:** DRAFT — PRE-PROVISIONING  
**Branch:** `azure-a1-f1`  
**Base SHA:** `26eef3df9dea6c8f1bfb763db8a43192223f3e3f`  
**Target region:** Qatar Central  
**Environment:** PREPROD / SYNTHETIC_ONLY  
**Real AMEC data allowed:** NO

## 1. Purpose

This appendix defines the F1 Azure deployment path for ProposalOps because Azure Container Apps is not exposed to this subscription in Qatar Central.

F1 is the approved fallback:

- Azure App Service for Linux containers
- triggered/scheduled WebJob for background worker execution
- manual WebJob or controlled one-shot command for Alembic migrations
- Azure Database for PostgreSQL Flexible Server
- Azure Container Registry
- Azure Key Vault
- Log Analytics + Application Insights
- Microsoft Entra ID authentication

No Azure resources are to be provisioned from this appendix until the A0 gates are complete and Owner GO is recorded.

## 2. Verified Azure Evidence

- App Service Linux: available in Qatar Central
- Initial App Service candidate: Basic B1
- ACR Basic: available in Qatar Central
- Key Vault: available in Qatar Central
- Log Analytics: available in Qatar Central
- Application Insights: available in Qatar Central
- Microsoft Foundry resource: available in Qatar Central
- Azure Container Apps: not available in Qatar Central for this subscription
- PostgreSQL Flexible Server: currently restricted for this subscription in Qatar Central
- PostgreSQL Qatar Central region-access request: pending

PostgreSQL remains a hard blocker for A1 provisioning.

## 3. Verified Repository Baseline

- Repository: `asamiibra/AMEC-Permits-Ops`
- Branch baseline: `main`
- Base SHA: `26eef3df9dea6c8f1bfb763db8a43192223f3e3f`
- Application: FastAPI + React/Vite modular monolith
- Target PostgreSQL major: 16
- Alembic head: `0058_source_intake_ledger`
- Backend image base: `python:3.12-slim`
- Backend Alpine image: NO
- Backend port: `8000`
- Backend entrypoint:
  `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Frontend build:
  `tsc -b && vite build`
- Transactional outbox claim / complete / recovery logic exists
- Current authentication remains development-header based and must be replaced for Azure preprod

## 4. F1 Target Architecture

```text
Browser
   |
   | HTTPS
   v
Azure App Service — Qatar Central
   |
   +-- ProposalOps web/API runtime
   |
   +-- Triggered/Scheduled WebJob
   |      |
   |      +-- transactional outbox worker
   |
   +-- Manual/Controlled Migration Job
          |
          +-- Alembic upgrade

   |
   +--> PostgreSQL Flexible Server 16
   +--> Key Vault
   +--> Application Insights / Log Analytics

Azure Container Registry
   |
   +--> immutable ProposalOps application image
