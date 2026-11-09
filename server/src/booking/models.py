import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


def new_booking_id() -> str:
    return str(uuid.uuid4())


class Slot(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    provider = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ["start", "id"]

    def __str__(self):
        return f"{self.id} ({self.provider})"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed"
        CANCELLED = "cancelled"

    id = models.CharField(primary_key=True, max_length=36, default=new_booking_id)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="bookings")
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=320, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CONFIRMED
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            # The database refuses a second confirmed booking for one slot
            models.UniqueConstraint(
                fields=["slot"],
                condition=Q(status="confirmed"),
                name="one_confirmed_per_slot",
            )
        ]

    def __str__(self):
        return f"{self.id} ({self.status})"


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255, unique=True)
    body_hash = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField()
    response = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)


class BookingAttempt(models.Model):
    email = models.CharField(max_length=320)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["email", "created_at"])]
