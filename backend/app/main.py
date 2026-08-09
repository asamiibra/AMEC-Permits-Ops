import json
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from .config.settings import get_settings
from .db import SessionLocal, init_db
from .models import ConsultancyOffice
from .api.routers import router
from .api.week2_routers import router as week2_router, mock_router as week2_mock_router
from .api.week3_routers import router as week3_router
from .api.reconciliation_routers import router as reconciliation_router
from .api.week45_routers import router as week45_router
from .api.week7_routers import router as week7_router
from .api.week8_routers import router as week8_router
from .api.week9_routers import router as week9_router
from .api.week10_routers import router as week10_router
from .api.week11_routers import router as week11_router
from .api.week12_routers import router as week12_router
from .api.week13_routers import router as week13_router
from .api.week14_routers import router as week14_router
from .api.expansion_routers import router as expansion_router
from .api.recovery_routers import router as recovery_router
from .api.e5_e6_routers import router as e5_e6_router

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format='%(message)s')
logger = logging.getLogger("permitops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PermitOps Build Week 8 Lineage + Validity", version="0.8.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "PUT"], allow_headers=["*"])


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Correlation-ID")
    correlation_id = incoming or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(json.dumps({"event": "request", "method": request.method, "path": request.url.path, "correlation_id": correlation_id}))
    return response


@app.exception_handler(Exception)
async def safe_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error", extra={"correlation_id": getattr(request.state, "correlation_id", None)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "correlation_id": getattr(request.state, "correlation_id", None)})


@app.get("/health")
def health(): return {"status": "ok", "service": "permitops", "environment": settings.app_env, "synthetic_only": settings.synthetic_only}


@app.get("/api/office")
def office():
    with SessionLocal() as db:
        record = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
        if not record:
            return JSONResponse(status_code=503, content={"detail": "Seed office not found"})
        return {"office_code": record.office_code, "name_en": record.name_en, "name_ar": record.name_ar, "synthetic": True}


@app.get("/api/dashboard")
def dashboard():
    from .db import SessionLocal
    from .models import Project, PermitApplication, ApplicationStatus, RaidItem, DiscoveryDecision, DecisionStatus, MinistryInquiry, InquiryStatus
    from sqlalchemy import select, func
    with SessionLocal() as db:
        return {"active_projects": db.scalar(select(func.count(Project.id)).where(Project.status == "ACTIVE")) or 0,
                "applications_by_status": {s.value: db.scalar(select(func.count(PermitApplication.id)).where(PermitApplication.application_status == s)) or 0 for s in ApplicationStatus},
                "returned_applications": db.scalar(select(func.count(PermitApplication.id)).where(PermitApplication.application_status == ApplicationStatus.RETURNED)) or 0,
                "open_raid_items": db.scalar(select(func.count(RaidItem.id)).where(RaidItem.status == "OPEN")) or 0,
                "pending_decisions": db.scalar(select(func.count(DiscoveryDecision.id)).where(DiscoveryDecision.status.in_([DecisionStatus.UNKNOWN, DecisionStatus.BLOCKED]))) or 0,
                "inquiries_not_asked": db.scalar(select(func.count(MinistryInquiry.id)).where(MinistryInquiry.status == InquiryStatus.NOT_ASKED)) or 0}


@app.get("/api/adapters/health")
def adapter_health():
    from .adapters.synology.adapter import MockSynologyAdapter
    from .adapters.excel.adapter import MockExcelAdapter
    from .adapters.municipality.adapter import MockMunicipalityAdapter
    from pathlib import Path
    root = Path(settings.mock_systems_root)
    return {"synology": MockSynologyAdapter(str(root / "synology")).health_check(), "excel": MockExcelAdapter(str(root / "excel/permit_tracker.xlsx")).health_check(), "municipality": MockMunicipalityAdapter({}).health_check()}


@app.get("/mock-authority/applications")
def mock_authority_applications():
    from .db import SessionLocal
    from .models import PermitApplication
    from sqlalchemy import select
    with SessionLocal() as db:
        return [{"id": a.id, "request_number": a.external_request_number, "project_number": a.project.project_number, "status": a.application_status, "repetition_count": a.repetition_count, "synthetic": True} for a in db.scalars(select(PermitApplication).order_by(PermitApplication.external_request_number)).all()]


@app.get("/mock-authority/applications/{application_id}")
def mock_authority_application(application_id: str):
    from .api.routers import application
    from .db import SessionLocal
    with SessionLocal() as db: return application(application_id, db)


@app.get("/mock-authority/applications/{application_id}/status")
def mock_authority_status(application_id: str):
    from .db import SessionLocal
    from .models import PermitApplication
    with SessionLocal() as db:
        a = db.get(PermitApplication, application_id)
        if not a: return JSONResponse(status_code=404, content={"detail": "Application not found"})
        return {"request_number": a.external_request_number, "status": a.application_status, "repetition_count": a.repetition_count, "synthetic": True}


@app.get("/mock-authority/applications/{application_id}/comments")
def mock_authority_comments(application_id: str):
    result = mock_authority_application(application_id)
    if isinstance(result, JSONResponse): return result
    return {"request_number": result["external_request_number"], "comments": result["comments"], "synthetic": True}

app.include_router(router)
app.include_router(week2_router)
app.include_router(week2_mock_router)
app.include_router(week3_router)
app.include_router(reconciliation_router)
app.include_router(week45_router)
app.include_router(week7_router)
app.include_router(week8_router)
app.include_router(week9_router)
app.include_router(week10_router)
app.include_router(week11_router)
app.include_router(week12_router)
app.include_router(week13_router)
app.include_router(week14_router)
app.include_router(expansion_router)
app.include_router(recovery_router)
app.include_router(e5_e6_router)
