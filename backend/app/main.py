import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from .api.admin_owner_ready import router as admin_owner_ready_router
from .api.bd_proposal_routers import router as bd_proposal_router
from .api.billing_invoice_routers import router as billing_invoice_router
from .api.completion_asbuilt_routers import router as completion_asbuilt_router
from .api.construction_routers import router as construction_router
from .api.contract_workspace_routers import router as contract_workspace_router
from .api.dashboard_inputs_routers import router as dashboard_inputs_router
from .api.dashboard_v2_routers import router as dashboard_v2_router
from .api.dependencies import trusted_current_principal
from .api.e5_e6_routers import router as e5_e6_router
from .api.expansion_routers import router as expansion_router
from .api.handover_closeout_routers import router as handover_closeout_router
from .api.master_content_routers import router as master_content_router
from .api.owner_decision_routers import router as owner_decision_router
from .api.permit_ux_routers import router as permit_ux_router
from .api.persona_issues_notifications import (
    router as persona_issues_notifications_router,
)
from .api.preparation_submission_routers import (
    router as preparation_submission_router,
)
from .api.project_engineering_routers import (
    router as project_engineering_router,
)
from .api.proposals_main_routers import (
    canonical_router as canonical_proposals_router,
)
from .api.proposals_main_routers import (
    router as proposals_main_router,
)
from .api.reconciliation_routers import (
    router as reconciliation_router,
)
from .api.recovery_routers import router as recovery_router
from .api.regulatory_context_routers import (
    router as regulatory_context_router,
)
from .api.routers import router
from .api.shared_domain_routers import router as shared_domain_router
from .api.week10_routers import router as week10_router
from .api.week11_routers import router as week11_router
from .api.week12_routers import router as week12_router
from .api.week13_routers import router as week13_router
from .api.week14_routers import router as week14_router
from .api.week2_routers import (
    mock_router as week2_mock_router,
)
from .api.week2_routers import router as week2_router
from .api.week3_routers import router as week3_router
from .api.week45_routers import router as week45_router
from .api.week7_routers import router as week7_router
from .api.week8_routers import router as week8_router
from .api.week9_routers import router as week9_router
from .api.work_routers import router as work_router
from .config.settings import get_settings
from .db import (
    SessionLocal,
    engine,
    prepare_database_for_runtime,
)
from .models import ConsultancyOffice
from .runtime_provenance import get_runtime_provenance


settings = get_settings()

logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    ),
    format="%(message)s",
)
logger = logging.getLogger("permitops")


def _fastapi_docs_config(
    app_env: str,
) -> dict[str, str | None]:
    # Azure preprod is Internet-facing and does not need a public
    # interactive API schema surface. DEV/TEST retain developer docs.
    if app_env.upper() == "AZURE-PREPROD":
        return {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    return {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_database_for_runtime()
    yield


app = FastAPI(
    title="ProposalOps · AMEC Proposal & Contract Workflow",
    version="0.8.0",
    lifespan=lifespan,
    **_fastapi_docs_config(settings.app_env),
)

API_AUTH_DEPENDENCIES = [
    Depends(current_principal),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "PUT",
    ],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(
    request: Request,
    call_next,
):
    started = time.perf_counter()
    incoming = request.headers.get(
        "X-Correlation-ID"
    )
    correlation_id = incoming or str(
        uuid.uuid4()
    )
    request.state.correlation_id = (
        correlation_id
    )

    response = await call_next(request)

    response.headers[
        "X-Correlation-ID"
    ] = correlation_id

    # API projections include mutable operational state. Vercel must not
    # serve a cached GET after an Owner writes the same configuration.
    if request.url.path.startswith("/api/"):
        response.headers[
            "Cache-Control"
        ] = "no-store, max-age=0"

    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "actor": (
                    request.headers.get(
                        "X-Dev-User"
                    )
                    or request.headers.get(
                        "X-Actor-Id"
                    )
                    or "anonymous"
                ),
                "status_code": (
                    response.status_code
                ),
                "outcome": (
                    "SUCCESS"
                    if response.status_code
                    < 400
                    else "FAILED"
                ),
                "latency_ms": round(
                    (
                        time.perf_counter()
                        - started
                    )
                    * 1000,
                    3,
                ),
                "entity_context": (
                    request.url.path.split(
                        "/"
                    )[:4]
                ),
            }
        )
    )

    return response


@app.exception_handler(Exception)
async def safe_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled request error",
        extra={
            "correlation_id": getattr(
                request.state,
                "correlation_id",
                None,
            )
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Internal server error"
            ),
            "correlation_id": getattr(
                request.state,
                "correlation_id",
                None,
            ),
        },
    )


@app.get("/health")
def health():
    database_configured = bool(
        os.getenv("DATABASE_URL")
    )
    database_dialect = (
        engine.dialect.name
    )
    connection_valid = False
    migration_versions: list[str] = []
    migration_state = "unknown"

    try:
        with engine.connect() as db:
            db.exec_driver_sql(
                "select 1"
            )

            try:
                migration_versions = list(
                    db.exec_driver_sql(
                        "select version_num "
                        "from alembic_version"
                    ).scalars()
                )
                migration_state = "present"
            except Exception:
                migration_state = "missing"

        connection_valid = True
    except Exception:
        connection_valid = False

    master_content_sor = {
        "mode": (
            "SYNTHETIC_TEST"
            if settings.synthetic_only
            else "REAL_CONFIGURED"
        ),
        "status": (
            "SYNTHETIC_DURABLE_DB_BACKED"
            if (
                os.getenv("VERCEL")
                and settings.synthetic_only
            )
            else (
                "SYNTHETIC_READY"
                if settings.synthetic_only
                else (
                    "REAL_SOR_REQUIRES_"
                    "VERIFICATION"
                )
            )
        ),
        "real_synology": (
            "NOT_CONFIGURED"
            if settings.synthetic_only
            else "CONFIGURED_NOT_VERIFIED"
        ),
    }

    storage_health = None

    try:
        from .storage.factory import (
            create_binary_store,
        )

        storage_health = (
            create_binary_store().health()
        )

        storage_health = {
            "state": storage_health.state,
            "provider_id": (
                storage_health.provider_id
            ),
            "latency_ms": (
                storage_health.latency_ms
            ),
            "detail": {
                "error_class": (
                    storage_health.detail.get(
                        "error_class"
                    )
                ),
                "synthetic": (
                    storage_health.detail.get(
                        "synthetic",
                        False,
                    )
                ),
            },
        }
    except Exception as exc:
        storage_health = {
            "state": "MISCONFIGURED",
            "provider_id": (
                settings.storage_provider
            ),
            "error_class": (
                type(exc).__name__
            ),
        }

    return {
        "status": "ok",
        "service": "permitops",
        "environment": settings.app_env,
        "synthetic_only": (
            settings.synthetic_only
        ),
        "database_configured": (
            database_configured
        ),
        "database_dialect": (
            database_dialect
        ),
        "database_durable": (
            database_dialect
            == "postgresql"
        ),
        "sqlite_fallback_active": (
            not database_configured
            and database_dialect
            == "sqlite"
        ),
        "database_connection_valid": (
            connection_valid
        ),
        "document_storage": (
            storage_health
        ),
        "alembic_versions": (
            migration_versions
        ),
        "alembic_state": migration_state,
        "master_content_sor": (
            master_content_sor
        ),
        "runtime_provenance": {
            **get_runtime_provenance(),
            "migration_head": (
                migration_versions[-1]
                if migration_versions
                else None
            ),
        },
    }


@app.get("/")
def api_root():
    return {
        "service": "ProposalOps API",
        "status": "ok",
        "environment": "synthetic",
    }


@app.get(
    "/api/office",
    dependencies=API_AUTH_DEPENDENCIES,
)
def office():
    with SessionLocal() as db:
        record = db.scalar(
            select(
                ConsultancyOffice
            ).where(
                ConsultancyOffice.office_code
                == "QEC-DOHA"
            )
        )

        if not record:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Seed office not found"
                    )
                },
            )

        return {
            "office_code": (
                record.office_code
            ),
            "name_en": record.name_en,
            "name_ar": record.name_ar,
            "synthetic": True,
        }


@app.get(
    "/api/dashboard",
    dependencies=API_AUTH_DEPENDENCIES,
)
def dashboard():
    from sqlalchemy import func

    from .models import (
        ApplicationStatus,
        DecisionStatus,
        DiscoveryDecision,
        InquiryStatus,
        MinistryInquiry,
        PermitApplication,
        Project,
        RaidItem,
    )

    with SessionLocal() as db:
        return {
            "active_projects": (
                db.scalar(
                    select(
                        func.count(Project.id)
                    ).where(
                        Project.status
                        == "ACTIVE"
                    )
                )
                or 0
            ),
            "applications_by_status": {
                status.value: (
                    db.scalar(
                        select(
                            func.count(
                                PermitApplication.id
                            )
                        ).where(
                            PermitApplication
                            .application_status
                            == status
                        )
                    )
                    or 0
                )
                for status
                in ApplicationStatus
            },
            "returned_applications": (
                db.scalar(
                    select(
                        func.count(
                            PermitApplication.id
                        )
                    ).where(
                        PermitApplication
                        .application_status
                        == ApplicationStatus
                        .RETURNED
                    )
                )
                or 0
            ),
            "open_raid_items": (
                db.scalar(
                    select(
                        func.count(
                            RaidItem.id
                        )
                    ).where(
                        RaidItem.status
                        == "OPEN"
                    )
                )
                or 0
            ),
            "pending_decisions": (
                db.scalar(
                    select(
                        func.count(
                            DiscoveryDecision.id
                        )
                    ).where(
                        DiscoveryDecision.status
                        .in_(
                            [
                                DecisionStatus
                                .UNKNOWN,
                                DecisionStatus
                                .BLOCKED,
                            ]
                        )
                    )
                )
                or 0
            ),
            "inquiries_not_asked": (
                db.scalar(
                    select(
                        func.count(
                            MinistryInquiry.id
                        )
                    ).where(
                        MinistryInquiry.status
                        == InquiryStatus
                        .NOT_ASKED
                    )
                )
                or 0
            ),
        }


@app.get(
    "/api/adapters/health",
    dependencies=API_AUTH_DEPENDENCIES,
)
def adapter_health():
    from pathlib import Path

    from .adapters.excel.adapter import (
        MockExcelAdapter,
    )
    from .adapters.municipality.adapter import (
        MockMunicipalityAdapter,
    )
    from .adapters.synology.adapter import (
        MockSynologyAdapter,
    )
    from .storage.factory import (
        create_binary_store,
    )

    root = Path(
        settings.mock_systems_root
    )

    binary_store = (
        create_binary_store()
    )
    binary_store_health = (
        binary_store.health()
    )

    return {
        "synology": MockSynologyAdapter(
            str(root / "synology")
        ).health_check(),
        "synology_configuration": {
            "mode": (
                settings.synology_mode.upper()
            ),
            "endpoint_configured": bool(
                settings.synology_endpoint
            ),
            "share_configured": bool(
                settings.synology_share
            ),
            "secret_reference_configured": (
                bool(
                    settings
                    .synology_secret_ref
                )
            ),
            "raw_endpoint_exposed": False,
        },
        "binary_store": {
            "provider": (
                settings.storage_provider
            ),
            "state": (
                binary_store_health.state
            ),
            "provider_id": (
                binary_store_health
                .provider_id
            ),
            "capabilities": (
                binary_store
                .capabilities()
                .__dict__
            ),
        },
        "master_content_sor": {
            "mode": (
                "SYNTHETIC_TEST"
                if settings.synthetic_only
                else "REAL_CONFIGURED"
            ),
            "status": (
                "SYNTHETIC_DURABLE_"
                "DB_BACKED"
                if (
                    os.getenv("VERCEL")
                    and settings.synthetic_only
                )
                else (
                    "SYNTHETIC_READY"
                    if settings.synthetic_only
                    else (
                        "REAL_SOR_REQUIRES_"
                        "VERIFICATION"
                    )
                )
            ),
            "real_synology": (
                "NOT_CONFIGURED"
                if settings.synthetic_only
                else (
                    "CONFIGURED_NOT_VERIFIED"
                )
            ),
        },
        "excel": MockExcelAdapter(
            str(
                root
                / "excel"
                / "permit_tracker.xlsx"
            )
        ).health_check(),
        "municipality": (
            MockMunicipalityAdapter(
                {}
            ).health_check()
        ),
    }


@app.get(
    "/mock-authority/applications",
    dependencies=API_AUTH_DEPENDENCIES,
)
def mock_authority_applications():
    from .models import (
        PermitApplication,
    )

    with SessionLocal() as db:
        applications = db.scalars(
            select(
                PermitApplication
            ).order_by(
                PermitApplication
                .external_request_number
            )
        ).all()

        return [
            {
                "id": application.id,
                "request_number": (
                    application
                    .external_request_number
                ),
                "project_number": (
                    application.project
                    .project_number
                ),
                "status": (
                    application
                    .application_status
                ),
                "repetition_count": (
                    application
                    .repetition_count
                ),
                "synthetic": True,
            }
            for application
            in applications
        ]


@app.get(
    "/mock-authority/applications/{application_id}",
    dependencies=API_AUTH_DEPENDENCIES,
)
def mock_authority_application(
    application_id: str,
):
    from .api.routers import application

    with SessionLocal() as db:
        return application(
            application_id,
            db,
        )


@app.get(
    "/mock-authority/applications/{application_id}/status",
    dependencies=API_AUTH_DEPENDENCIES,
)
def mock_authority_status(
    application_id: str,
):
    from .models import (
        PermitApplication,
    )

    with SessionLocal() as db:
        application = db.get(
            PermitApplication,
            application_id,
        )

        if not application:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": (
                        "Application not found"
                    )
                },
            )

        return {
            "request_number": (
                application
                .external_request_number
            ),
            "status": (
                application
                .application_status
            ),
            "repetition_count": (
                application
                .repetition_count
            ),
            "synthetic": True,
        }


@app.get(
    "/mock-authority/applications/{application_id}/comments",
    dependencies=API_AUTH_DEPENDENCIES,
)
def mock_authority_comments(
    application_id: str,
):
    result = mock_authority_application(
        application_id
    )

    if isinstance(
        result,
        JSONResponse,
    ):
        return result

    return {
        "request_number": (
            result[
                "external_request_number"
            ]
        ),
        "comments": result["comments"],
        "synthetic": True,
    }


app.include_router(
    router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week2_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week2_mock_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week3_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    reconciliation_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week45_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week11_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    persona_issues_notifications_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    admin_owner_ready_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    work_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week7_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week8_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week9_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week10_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week12_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week13_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    week14_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    expansion_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    canonical_proposals_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    recovery_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    e5_e6_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    proposals_main_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    master_content_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    bd_proposal_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    dashboard_inputs_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    contract_workspace_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    project_engineering_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    owner_decision_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    shared_domain_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    dashboard_v2_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    preparation_submission_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    regulatory_context_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    permit_ux_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    billing_invoice_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    construction_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    completion_asbuilt_router,
    dependencies=API_AUTH_DEPENDENCIES,
)

app.include_router(
    handover_closeout_router,
    dependencies=API_AUTH_DEPENDENCIES,
)
