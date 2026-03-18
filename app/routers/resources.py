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
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models import Resource
from app.services.ai_generator import GENERATORS
from app.services.export_service import export_pdf, export_docx, export_pptx
from app.auth_utils import get_user_from_cookie

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

RESOURCE_TYPE_LABELS = {
    "lesson": "Lesson Plan",
    "worksheet": "Worksheet",
    "scheme": "Scheme of Work",
    "slides": "Slide Outline",
}

KEY_STAGES = ["EYFS", "KS1", "KS2", "KS3", "KS4 (GCSE)", "A Level", "BTEC", "T Level"]


def _base_ctx(request: Request, current_user=None) -> dict:
    return {
        "request": request,
        "resource_type_labels": RESOURCE_TYPE_LABELS,
        "key_stages": KEY_STAGES,
        "current_user": current_user,
    }


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    notice = request.query_params.get("notice", "")
    ctx = _base_ctx(request, user)
    ctx["notice"] = notice

    # Compute locked_types for unverified users
    locked_types: list[str] = []
    if not user.is_school_verified and user.role != "admin":
        for rtype in RESOURCE_TYPE_LABELS:
            count = (
                db.query(Resource)
                .filter(Resource.user_id == user.id, Resource.type == rtype)
                .count()
            )
            if count >= 1:
                locked_types.append(rtype)
    ctx["locked_types"] = locked_types

    return templates.TemplateResponse("index.html", ctx)


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
    user = get_user_from_cookie(request, db)
    if not user:
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/login"
        return response

    # Unverified users are limited to 1 resource per type
    if not user.is_school_verified and user.role != "admin":
        existing_count = (
            db.query(Resource)
            .filter(Resource.user_id == user.id, Resource.type == resource_type)
            .count()
        )
        if existing_count >= 1:
            type_label = RESOURCE_TYPE_LABELS.get(resource_type, resource_type)
            locked_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Type Locked – BloomsBuilder</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background: linear-gradient(135deg, #ddeef5 0%, #eaf4f8 35%, #d8eaf2 70%, #e4f0f6 100%); min-height: 100vh; display:flex; align-items:center; justify-content:center; }}
  </style>
</head>
<body>
  <div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.55);box-shadow:0 8px 32px rgba(64,101,123,0.14);border-radius:18px;" class="max-w-md w-full mx-4 p-10 text-center">
    <div class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5" style="background:rgba(95,156,179,0.12);">
      <svg class="w-8 h-8" style="color:#5f9cb3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m0 0v2m0-2h2m-2 0H9m3-4V9m0 0a3 3 0 100-6 3 3 0 000 6z"/>
      </svg>
    </div>
    <h1 class="text-2xl font-bold mb-2" style="color:#2e4e61;">{type_label} Locked</h1>
    <p class="text-sm mb-6" style="color:#40657b;">
      Unverified accounts can create <strong>1 resource per type</strong>.
      You've already created a {type_label}.
      Verify your school email to unlock unlimited access.
    </p>
    <a href="/" style="display:inline-block;background:linear-gradient(135deg,#5f9cb3,#40657b);color:white;padding:0.625rem 1.5rem;border-radius:8px;font-weight:600;font-size:0.875rem;text-decoration:none;box-shadow:0 4px 14px rgba(95,156,179,0.35);">
      Back to Home
    </a>
  </div>
</body>
</html>
"""
            return HTMLResponse(content=locked_html, status_code=200)

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
        user_id=user.id,
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

    response = Response(status_code=200)
    response.headers["HX-Redirect"] = f"/resources/{resource.id}"
    return response


# ---------------------------------------------------------------------------
# Resource preview
# ---------------------------------------------------------------------------

@router.get("/resources/{resource_id}", response_class=HTMLResponse)
async def preview_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Teachers can only view their own resources; admin can view all
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    data = json.loads(resource.structured_output)
    ctx = _base_ctx(request, user)
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
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    query = db.query(Resource)
    if user.role != "admin":
        query = query.filter(Resource.user_id == user.id)
    if filter_type and filter_type in RESOURCE_TYPE_LABELS:
        query = query.filter(Resource.type == filter_type)
    resources = query.order_by(Resource.created_at.desc()).all()

    ctx = _base_ctx(request, user)
    ctx["resources"] = resources
    ctx["filter_type"] = filter_type or ""
    return templates.TemplateResponse("library.html", ctx)


# ---------------------------------------------------------------------------
# Delete resource
# ---------------------------------------------------------------------------

@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    db.delete(resource)
    db.commit()
    return Response(status_code=200, content="")


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

@router.get("/export/{resource_id}/pdf")
async def export_resource_pdf(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    try:
        pdf_bytes = export_pdf(resource)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        logger.error("PDF export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="PDF generation failed.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'},
    )


@router.get("/export/{resource_id}/docx")
async def export_resource_docx(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    try:
        docx_bytes = export_docx(resource)
    except Exception as exc:
        logger.error("DOCX export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="DOCX generation failed.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'},
    )


@router.get("/export/{resource_id}/pptx")
async def export_resource_pptx(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorised")
    if resource.type != "slides":
        raise HTTPException(status_code=400, detail="PPTX export is only available for Slide Outline resources.")

    try:
        pptx_bytes = export_pptx(resource)
    except Exception as exc:
        logger.error("PPTX export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="PPTX generation failed.")

    safe_title = resource.title.replace(" ", "_")[:60]
    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.pptx"'},
    )
