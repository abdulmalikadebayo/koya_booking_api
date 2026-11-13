import math
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import connection, transaction

from .models import BookingAttempt

WINDOW = timedelta(seconds=60)
MAX_ATTEMPTS = 5


def usable_email(data) -> str | None:
    """The normalised email of a request body, or None if it has no valid one."""
    email = data.get("email") if isinstance(data, dict) else None
    if not isinstance(email, str):
        return None
    email = email.strip().lower()
    try:
        validate_email(email)
    except DjangoValidationError:
        return None
    return email


def check_and_record(email: str, now: datetime) -> int | None:
    """Record an attempt for email.

    Returns None when allowed, or the whole seconds (at least 1) to wait.
    Committed on its own so a failed booking still counts.
    """
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))", [f"rate:{email}"]
            )
        cutoff = now - WINDOW
        BookingAttempt.objects.filter(email=email, created_at__lte=cutoff).delete()
        recent = list(
            BookingAttempt.objects.filter(email=email)
            .order_by("created_at")
            .values_list("created_at", flat=True)
        )
        if len(recent) >= MAX_ATTEMPTS:
            wait = (recent[0] + WINDOW - now).total_seconds()
            return max(1, math.ceil(wait))
        BookingAttempt.objects.create(email=email, created_at=now)
        return None
