from django.db import transaction
from django.db.models import Exists, OuterRef

from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, BookingAttempt, IdempotencyRecord, Slot
from .serializers import ResetSerializer, booking_to_dict, slot_to_dict


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
        slot = Slot.objects.get(pk=request.data["slot_id"])
        booking = Booking.objects.create(
            slot=slot, name=request.data["name"], email=request.data["email"]
        )
        return Response(booking_to_dict(booking), status=201)


class BookingDetailAPIView(APIView):
    def get(self, request, id):
        try:
            booking = Booking.objects.get(pk=id)
        except Booking.DoesNotExist:
            raise NotFound("booking not found")
        return Response(booking_to_dict(booking))
