"""Option B document editor boundary.

The browser exchanges JSON editor models. DOCX parsing and export remain
server responsibilities, and export always starts from the uploaded original
package and applies anchored mutations.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from ..services.proposal_document_package import DocumentPackageError, apply_text_mutations, package_parts
from ..services.proposal_editor_model import editor_diff_to_mutations, import_editor_model, tracked_changes

router = APIRouter(prefix="/api/proposals-v1/editor", tags=["proposal-editor-option-b"])
MAX_UPLOAD = 64 * 1024 * 1024


async def _docx(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "DOCX_PACKAGE_SIZE_LIMIT")
    try:
        package_parts(data)
    except DocumentPackageError as exc:
        raise HTTPException(422, str(exc)) from exc
    return data


def _model(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "EDITOR_MODEL_JSON_REQUIRED") from exc
    if not isinstance(value, dict):
        raise HTTPException(422, "EDITOR_MODEL_OBJECT_REQUIRED")
    return value


@router.post("/import")
async def import_docx(file: UploadFile = File(...)):
    data = await _docx(file)
    return import_editor_model(data)


@router.post("/changes")
async def preview_changes(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...)):
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    # Re-import from bytes and compare the immutable node identity. A client
    # cannot forge an anchor map or precondition by posting JSON alone.
    server_model = import_editor_model(data)
    if server_model.get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        mutations = editor_diff_to_mutations(imported, current)
        changes = tracked_changes(imported, current)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"changes": changes, "mutation_count": len(mutations), "export_path": "ORIGINAL_PACKAGE_TARGETED_MUTATIONS"}


@router.post("/export")
async def export_docx(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...)):
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    if import_editor_model(data).get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        mutations = editor_diff_to_mutations(imported, current)
        output = apply_text_mutations(data, mutations)
    except (ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return StreamingResponse(io.BytesIO(output), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": 'attachment; filename="proposal-edited.docx"', "X-Proposal-Export-Path": "ORIGINAL_PACKAGE_TARGETED_MUTATIONS"})


@router.post("/preview")
async def true_render_preview(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...)):
    """Render the actual mutated package with the host Office pipeline."""
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    if import_editor_model(data).get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        output = apply_text_mutations(data, editor_diff_to_mutations(imported, current))
    except (ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, str(exc)) from exc
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        raise HTTPException(503, "TRUE_RENDER_PIPELINE_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="proposal-preview-") as directory:
        source = os.path.join(directory, "proposal.docx")
        with open(source, "wb") as handle:
            handle.write(output)
        try:
            subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", directory, source], check=True, timeout=45, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as exc:
            raise HTTPException(503, "TRUE_RENDER_FAILED") from exc
        pdf = os.path.join(directory, "proposal.pdf")
        if not os.path.isfile(pdf):
            raise HTTPException(503, "TRUE_RENDER_OUTPUT_MISSING")
        with open(pdf, "rb") as handle:
            rendered = handle.read()
    return StreamingResponse(io.BytesIO(rendered), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="proposal-preview.pdf"', "X-Proposal-Render": "TRUE_DOCX_TO_PDF"})
