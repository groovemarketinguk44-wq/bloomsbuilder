"""
Resources Router
----------------
Handles all routes for resource generation, preview, library, and export.
"""

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models import Resource
from app.services.ai_generator import GENERATORS
from app.services.export_service import export_pdf, export_docx, export_pptx

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ---------------------------------------------------------------------------
# Template helpers injected into every template context
# ---------------------------------------------------------------------------

RESOURCE_TYPE_LABELS = {
    "lesson": "Lesson Plan",
    "worksheet": "Worksheet",
    "scheme": "Scheme of Work",
    "slides": "Slide Outline",
}

KEY_STAGES = ["KS1", "KS2", "KS3", "KS4", "KS5"]


def _base_ctx(request: Request) -> dict:
    return {
        "request": request,
        "resource_type_labels": RESOURCE_TYPE_LABELS,
        "key_stages": KEY_STAGES,
        "ai_key_set": bool(os.getenv("AI_API_KEY")),
    }


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", _base_ctx(request))


# ---------------------------------------------------------------------------
# Generate resource  (HTMX POST → HX-Redirect to preview)
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_resource(
    request: Request,
    resource_type: str = Form(...),
    subject: str = Form(...),
    key_stage: str = Form(...),
    topic: str = Form(...),
    additional_instructions: str = Form(""),
    db: Session = Depends(get_db),
):
    if resource_type not in GENERATORS:
        raise HTTPException(status_code=422, detail=f"Unknown resource type: {resource_type}")

    generator = GENERATORS[resource_type]
    structured_data = await generator(
        subject=subject,
        key_stage=key_stage,
        topic=topic,
        additional_instructions=additional_instructions,
    )

    title = structured_data.get("title", f"{topic} – {RESOURCE_TYPE_LABELS.get(resource_type, resource_type)}")
    input_prompt = (
        f"Type: {resource_type} | Subject: {subject} | Key Stage: {key_stage} | Topic: {topic}"
        + (f" | Notes: {additional_instructions}" if additional_instructions else "")
    )

    resource = Resource(
        type=resource_type,
        title=title,
        subject=subject,
        key_stage=key_stage,
        topic=topic,
        input_prompt=input_prompt,
        structured_output=json.dumps(structured_data),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # HTMX redirect to the preview page
    response = Response(status_code=200)
    response.headers["HX-Redirect"] = f"/resources/{resource.id}"
    return response


# ---------------------------------------------------------------------------
# Resource preview
# ---------------------------------------------------------------------------

@router.get("/resources/{resource_id}", response_class=HTMLResponse)
async def preview_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    data = json.loads(resource.structured_output)
    ctx = _base_ctx(request)
    ctx["resource"] = resource
    ctx["data"] = data
    return templates.TemplateResponse("preview.html", ctx)


# ---------------------------------------------------------------------------
# Resource library
# ---------------------------------------------------------------------------

@router.get("/library", response_class=HTMLResponse)
async def library(
    request: Request,
    filter_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Resource)
    if filter_type and filter_type in RESOURCE_TYPE_LABELS:
        query = query.filter(Resource.type == filter_type)
    resources = query.order_by(Resource.created_at.desc()).all()
    ctx = _base_ctx(request)
    ctx["resources"] = resources
    ctx["filter_type"] = filter_type or ""
    return templates.TemplateResponse("library.html", ctx)


# ---------------------------------------------------------------------------
# Delete resource  (HTMX DELETE → removes card from library)
# ---------------------------------------------------------------------------

@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(resource)
    db.commit()
    # Return empty 200 – HTMX will swap the target out of the DOM
    return Response(status_code=200, content="")


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

@router.get("/export/{resource_id}/pdf")
async def export_resource_pdf(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    try:
        pdf_bytes = export_pdf(resource)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        logger.error("PDF export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="PDF generation failed. Check server logs.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'},
    )


@router.get("/export/{resource_id}/docx")
async def export_resource_docx(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    try:
        docx_bytes = export_docx(resource)
    except Exception as exc:
        logger.error("DOCX export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="DOCX generation failed. Check server logs.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'},
    )


@router.get("/export/{resource_id}/pptx")
async def export_resource_pptx(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.type != "slides":
        raise HTTPException(status_code=400, detail="PPTX export is only available for Slide Outline resources.")
    try:
        pptx_bytes = export_pptx(resource)
    except Exception as exc:
        logger.error("PPTX export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="PPTX generation failed. Check server logs.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.pptx"'},
    )
