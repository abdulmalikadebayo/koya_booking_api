from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, BookingAttempt, IdempotencyRecord, Slot
from . import clock
from .errors import Conflict
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


class BookingListCreateAPIView(APIView):
    def post(self, request):
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
