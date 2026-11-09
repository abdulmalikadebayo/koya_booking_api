from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, BookingAttempt, IdempotencyRecord, Slot
from . import clock, idempotency
from .pagination import decode_cursor, encode_cursor
from .errors import Conflict, UnprocessableEntity
from .serializers import (
    NewBookingSerializer,
    ResetSerializer,
    booking_to_dict,
    slot_to_dict,
)


class NotFoundAPIView(APIView):
    """Catch-all so unknown routes return the JSON error shape."""

    def handle(self, request, *args, **kwargs):
        raise NotFound("not found")

    get = post = put = patch = delete = handle


class ResetAPIView(APIView):
    def post(self, request):
        serializer = ResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slots = serializer.validated_data["slots"]

        with transaction.atomic():
            Booking.objects.all().delete()
            IdempotencyRecord.objects.all().delete()
            BookingAttempt.objects.all().delete()
            Slot.objects.all().delete()
            Slot.objects.bulk_create([Slot(**s) for s in slots])

        return Response({"slots": len(slots)}, status=200)


class SlotListAPIView(APIView):
    def get(self, request):
        confirmed = Booking.objects.filter(
            slot=OuterRef("pk"), status=Booking.Status.CONFIRMED
        )
        slots = Slot.objects.annotate(taken=Exists(confirmed)).order_by("start", "id")

        provider = request.query_params.get("provider")
        if provider is not None:
            slots = slots.filter(provider=provider)

        for slot in slots:
            slot.available = not slot.taken
        return Response({"slots": [slot_to_dict(s) for s in slots]})


DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def parse_limit(raw) -> int:
    if raw is None:
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        raise ValidationError("limit must be an integer from 1 to 50")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValidationError("limit must be an integer from 1 to 50")
    return limit


class BookingListCreateAPIView(APIView):
    def get(self, request):
        email = request.query_params.get("email", "").strip().lower()
        if not email:
            raise ValidationError("email is required")
        limit = parse_limit(request.query_params.get("limit"))

        bookings = Booking.objects.filter(email=email).order_by("created_at", "id")
        cursor = request.query_params.get("cursor")
        if cursor:
            try:
                created_at, last_id = decode_cursor(cursor)
            except ValueError:
                raise ValidationError("invalid cursor")
            bookings = bookings.filter(
                Q(created_at__gt=created_at) | Q(created_at=created_at, id__gt=last_id)
            )

        rows = list(bookings[: limit + 1])
        page = rows[:limit]
        next_cursor = (
            encode_cursor(page[-1].created_at, page[-1].id)
            if len(rows) > limit
            else None
        )
        return Response(
            {"bookings": [booking_to_dict(b) for b in page], "next_cursor": next_cursor}
        )

    def post(self, request):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return self.create_booking(request)

        digest = idempotency.body_hash(request.data)
        with transaction.atomic():
            idempotency.acquire_key_lock(key)
            record = idempotency.find(key)
            if record:
                if record.body_hash != digest:
                    raise UnprocessableEntity(
                        "Idempotency-Key was already used with a different body"
                    )
                return Response(record.response, status=record.status_code)
            response = self.create_booking(request)
            idempotency.store(key, digest, response.status_code, response.data)
            return response

    def create_booking(self, request):
        serializer = NewBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                # Row lock: concurrent bookings for one slot queue up here
                try:
                    slot = Slot.objects.select_for_update().get(pk=data["slot_id"])
                except Slot.DoesNotExist:
                    raise NotFound("slot not found")
                if slot.start <= clock.now():
                    raise ValidationError("slot has already started")
                if slot.bookings.filter(status=Booking.Status.CONFIRMED).exists():
                    raise Conflict("slot already booked")
                booking = Booking.objects.create(
                    slot=slot, name=data["name"], email=data["email"]
                )
        except IntegrityError:
            # Backstop: the one_confirmed_per_slot constraint refused a duplicate
            raise Conflict("slot already booked")
        return Response(booking_to_dict(booking), status=201)


class BookingDetailAPIView(APIView):
    def get(self, request, id):
        try:
            booking = Booking.objects.get(pk=id)
        except Booking.DoesNotExist:
            raise NotFound("booking not found")
        return Response(booking_to_dict(booking))

    def delete(self, request, id):
        with transaction.atomic():
            try:
                booking = Booking.objects.select_for_update().get(pk=id)
            except Booking.DoesNotExist:
                raise NotFound("booking not found")
            if booking.status == Booking.Status.CANCELLED:
                raise Conflict("booking already cancelled")
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status"])
        return Response(booking_to_dict(booking))
