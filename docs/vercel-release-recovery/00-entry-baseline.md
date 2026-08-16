# Vercel Release Recovery — Entry Baseline

Captured before repository mutation on 2026-08-15.

## Repository

- Working directory: `/Users/ahmedsami/Desktop/Qatar Permitting Tool/Dev`
- Git top level: `/Users/ahmedsami/Desktop/Qatar Permitting Tool/Dev`
- Branch: `branch/owner-form-simple-dashboard`
- Entry SHA: `fc619748dc390af58924378b02d54b59f360a54a`
- Upstream: `origin/branch/owner-form-simple-dashboard`
- Remote SHA at entry: `fc619748dc390af58924378b02d54b59f360a54a`
- Local/remote parity at entry: `1`
- Worktree at entry: clean
- Unknown changes at entry: `0`
- Unrelated staged changes at entry: `0`

## Remotes and project linkage

- Origin: `https://github.com/asamiibra/AMEC-Permits-Ops.git`
- Root Vercel project linkage: `.vercel/project.json`
- Frontend Vercel project linkage: `frontend/.vercel/project.json`
- Project: `amec-permits-ops`
- Project ID: `prj_VFnILYm6UhREXZMV0h3ltXVz2nC4`
- Team ID: `team_sbo1tPlVElgVFAhW4g4WelVB`
- Backend linkage: `backend/.vercel/project.json` (`amec-permits-ops-backend`)
- Frontend project config: `frontend/vercel.json`
- Backend project config: `backend/vercel.json`
- Frontend package root: `frontend`

## Git identity at entry

- Local author name: `NOT CONFIGURED`
- Local author email: `NOT CONFIGURED`
- Effective historical commit email classification: `INVALID_LOCALHOST_STYLE`
- Historical commit email is intentionally not repeated here; it ends in `.local`.

## Protected fixtures

The repository README identifies the canonical workbook as `mock-systems/excel/permit_tracker.xlsx`.

| Path | SHA-256 before | Protection |
|---|---|---|
| `mock-systems/excel/permit_tracker.xlsx` | `fcfc1687e193e91eb37da527a79ed5942ae1f33bd45f5bb8a2c83f598a176b8b` | primary protected fixture |
| `mock-systems/excel/permit_tracker 2.xlsx` | `3eb887e87bf0d5695a570e8aa1e6c917d646176c77e1b978d6387681d58f1be0` | tracked sibling fixture |
| `backend/mock-systems/excel/permit_tracker.xlsx` | `798a5553a686f5d5e72c50531556dd8e97a2bb0c6183476b16e2a06b971d3699` | backend copy |

## Historical release references

The historical SHAs supplied with this recovery request are present in the local object database, but the current branch is `branch/owner-form-simple-dashboard`, not `branch/ui-productionization`. They remain reference points for reconciliation and are not assumed to be the current release:

- Earlier UI closure: `1dfdded11af15cf7c86dc7149cc19232bd72371e`
- Icon closure: `4467c5532fc8aa19d48181e1debe1c109b643311`
- Historical tested/release: `e5b916d5a81dfdd72a93a769d49d015cf2c71866`
- Historical pushed evidence: `37eaa4da1503c1502170af0bb5c3eaef7a1f64b6`

## Deployment baseline

- Vercel CLI: not installed in the local shell at entry
- Production deployment metadata: pending non-mutating inspection
- Production alias/domain: pending non-mutating inspection
- Historical quota blocker: `api-deployments-free-per-day` (to be rechecked before any deployment call)
- Deployment attempts made by this recovery run at entry: `0`

## Scope controls

- No application redesign performed.
- No business/domain tables or migrations changed.
- No deployment attempted.
