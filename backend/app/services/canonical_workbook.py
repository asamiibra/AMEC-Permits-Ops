from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from ..fixtures.canonical import CANONICAL_PROJECTION_SHEET, CANONICAL_WORKBOOK_SHEETS
from ..fixtures.canonical import CANONICAL_PROJECT_IDS


PROJECTION_HEADERS = ["Project Number", "Canonical Plot Number", "Canonical PIN", "Rendering Version", "Municipality Request", "Projection Status"]
HUMAN_HEADERS = {
    "GENERAL FOLLOW UP": ["Project Number", "Project Name", "Client/Owner", "Status", "Permit Type", "Human Notes"],
    "DESIGN": ["Project Number", "Drawing Revision", "Design Lead", "Human Notes"],
    "Suppervission": ["Project Number", "Supervisor", "Review Status", "Human Notes"],
    "Services Provider": ["Project Number", "Provider", "Service Type", "Human Notes"],
}
HUMAN_ROWS = [
    (CANONICAL_PROJECT_IDS[0], "Al Noor Villa", "Synthetic Owner Group", "DRAFT", "Building Permit"),
    (CANONICAL_PROJECT_IDS[1], "West Bay Residence", "Synthetic Owner Group", "RETURNED", "Building Permit"),
    (CANONICAL_PROJECT_IDS[2], "Lusail Office Annex", "Synthetic Company", "UNDER_REVIEW", "Fit-out Permit"),
    (CANONICAL_PROJECT_IDS[3], "Pearl Community Clinic", "Synthetic Company", "APPROVED", "Renovation Permit"),
]


def ensure_canonical_workbook(path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    first = wb.active
    wb.remove(first)
    for sheet, headers in HUMAN_HEADERS.items():
        ws = wb.create_sheet(sheet)
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        if sheet == "GENERAL FOLLOW UP":
            for number, name, owner, status, permit_type in HUMAN_ROWS:
                ws.append([number, name, owner, status, permit_type, "Synthetic human-owned fixture cell"])
        else:
            for number, *_ in HUMAN_ROWS:
                ws.append([number, "R01", "Synthetic", "Synthetic human-owned fixture cell"])
    projection = wb.create_sheet(CANONICAL_PROJECTION_SHEET)
    projection.append(PROJECTION_HEADERS)
    for cell in projection[1]:
        cell.font = Font(bold=True)
    wb.properties.title = "PermitOps Synthetic MVP Dataset v1 — Recording-derived workbook"
    wb.properties.subject = "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED"
    wb.save(destination)
    return destination


def canonical_workbook_contract(path: str | Path) -> dict[str, Any]:
    wb = load_workbook(path, read_only=True, data_only=True)
    return {
        "workbook_identity": str(path),
        "required_sheets": CANONICAL_WORKBOOK_SHEETS,
        "sheets": wb.sheetnames,
        "row_identity": "GENERAL FOLLOW UP: Project Number exact match; sheet + row number retained",
        "human_owned_columns": {sheet: headers for sheet, headers in HUMAN_HEADERS.items()},
        "system_owned_projection": {"sheet": CANONICAL_PROJECTION_SHEET, "columns": PROJECTION_HEADERS[1:]},
        "write_policy": "Only PERMITOPS SYSTEM PROJECTION is writable by the system; human sheets are read-only.",
    }


def _lock_paths(path: Path) -> list[Path]:
    return [path.with_suffix(path.suffix + ".lock"), path.parent / ".permitops-workbook.lock"]


class WorkbookLockedError(RuntimeError):
    pass


def write_system_projection(path: str | Path, project_number: str, values: dict[str, Any]) -> dict[str, Any]:
    workbook_path = Path(path)
    if any(lock.exists() for lock in _lock_paths(workbook_path)):
        raise WorkbookLockedError("WORKBOOK_LOCKED_MANUAL_COPY_REQUIRED")
    wb = load_workbook(workbook_path)
    if CANONICAL_PROJECTION_SHEET not in wb.sheetnames:
        raise ValueError("CANONICAL_PROJECTION_SHEET_MISSING")
    ws = wb[CANONICAL_PROJECTION_SHEET]
    headers = [cell.value for cell in ws[1]]
    row = next((index for index in range(2, ws.max_row + 1) if ws.cell(index, 1).value == project_number), None)
    if row is None:
        row = ws.max_row + 1
        ws.cell(row, 1).value = project_number
    allowed = set(PROJECTION_HEADERS[1:])
    for key, value in values.items():
        if key in allowed:
            ws.cell(row, headers.index(key) + 1).value = value
    ws.cell(row, headers.index("Projection Status") + 1).value = values.get("Projection Status", "WRITTEN")
    with NamedTemporaryFile(prefix="permitops-excel-", suffix=".xlsx", dir=workbook_path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        wb.save(temporary_path)
        os.replace(temporary_path, workbook_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {"workbook_identity": str(workbook_path), "sheet": CANONICAL_PROJECTION_SHEET, "row_number": row, "row_key": project_number, "status": "WRITTEN", "owned_region_only": True}
