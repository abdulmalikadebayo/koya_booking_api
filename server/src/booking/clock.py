from django.utils import timezone


def now():
    """Single clock so tests can freeze time."""
    return timezone.now()
