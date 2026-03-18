"""
Plan definitions and limit helpers.
"""
from datetime import datetime, timezone

PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free":  {"lesson": 5,    "worksheet": 10,  "slides": 3,   "scheme": 1},
    "core":  {"lesson": 20,   "worksheet": 40,  "slides": 10,  "scheme": 3},
    "power": {"lesson": None, "worksheet": None, "slides": None, "scheme": None},
}

PLAN_NAMES  = {"free": "Free",        "core": "Core Teacher",       "power": "Power"}
PLAN_PRICES = {"free": "Free forever", "core": "£4.99 / month",     "power": "£14.99 / month"}
PLAN_COLOURS = {"free": "#5f9cb3",    "core": "#7c6bb5",            "power": "#d97706"}


def monthly_usage(db, user_id: int, resource_type: str) -> int:
    """Count resources of this type created this calendar month by user."""
    from app.models import Resource  # local import to avoid circular
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(Resource)
        .filter(Resource.user_id == user_id, Resource.type == resource_type,
                Resource.created_at >= start)
        .count()
    )


def is_at_limit(db, user, resource_type: str) -> bool:
    """Return True if user has hit their monthly limit for this resource type."""
    plan = getattr(user, "plan", "free") or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    cap = limits.get(resource_type)
    if cap is None:
        return False  # unlimited
    used = monthly_usage(db, user.id, resource_type)
    return used >= cap


def get_usage_summary(db, user) -> dict:
    """Return dict of {type: {"used": n, "cap": n|None}} for all types."""
    plan = getattr(user, "plan", "free") or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    result = {}
    for rtype, cap in limits.items():
        used = monthly_usage(db, user.id, rtype)
        result[rtype] = {"used": used, "cap": cap}
    return result
