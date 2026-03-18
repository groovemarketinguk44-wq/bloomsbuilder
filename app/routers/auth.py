import json
import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth_utils import (
    hash_password, verify_password, create_token,
    get_user_from_cookie, is_school_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

KEY_STAGES = ["EYFS", "KS1", "KS2", "KS3", "KS4 (GCSE)", "A Level", "BTEC", "T Level"]


def _base_ctx(request: Request, current_user=None) -> dict:
    return {
        "request": request,
        "current_user": current_user,
        "key_stages": KEY_STAGES,
    }


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    msg = request.query_params.get("msg", "")
    ctx = _base_ctx(request)
    ctx["msg"] = msg
    return templates.TemplateResponse("login.html", ctx)


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        ctx = _base_ctx(request)
        ctx["error"] = "Incorrect email or password."
        ctx["msg"] = ""
        return templates.TemplateResponse("login.html", ctx, status_code=401)

    if not user.is_active:
        ctx = _base_ctx(request)
        ctx["error"] = "Your account has been deactivated. Please contact support."
        ctx["msg"] = ""
        return templates.TemplateResponse("login.html", ctx, status_code=403)

    token = create_token(user.id, user.role)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token", token,
        httponly=True, max_age=60 * 60 * 24 * 7, samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("signup.html", _base_ctx(request))


@router.post("/signup")
async def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    school: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.lower().strip()

    # Check duplicate
    if db.query(User).filter(User.email == email).first():
        ctx = _base_ctx(request)
        ctx["error"] = "An account with that email already exists."
        ctx["values"] = {"first_name": first_name, "last_name": last_name, "email": email, "school": school}
        return templates.TemplateResponse("signup.html", ctx, status_code=400)

    # Collect selected key stages (checkboxes)
    form_data = await request.form()
    selected_ks = form_data.getlist("key_stages")

    verified = is_school_email(email)

    user = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        school=school.strip(),
        key_stages=json.dumps(selected_ks),
        hashed_password=hash_password(password),
        role="teacher",
        is_school_verified=verified,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.role)
    dest = "/?notice=unverified" if not verified else "/"
    response = RedirectResponse(dest, status_code=303)
    response.set_cookie(
        "access_token", token,
        httponly=True, max_age=60 * 60 * 24 * 7, samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    current_user = get_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    if current_user.role != "admin":
        return RedirectResponse("/", status_code=303)

    teachers = (
        db.query(User)
        .filter(User.role == "teacher")
        .order_by(User.created_at.desc())
        .all()
    )
    ctx = _base_ctx(request, current_user)
    ctx["teachers"] = teachers
    return templates.TemplateResponse("admin.html", ctx)


@router.post("/admin/users/{user_id}/delete")
async def admin_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_user_from_cookie(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_user_from_cookie(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/users/{user_id}/plan")
async def admin_set_plan(
    user_id: int, request: Request,
    plan: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_user_from_cookie(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    if plan not in ("free", "core", "power"):
        return RedirectResponse("/admin", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.plan = plan
        db.commit()
    return RedirectResponse("/admin", status_code=303)
