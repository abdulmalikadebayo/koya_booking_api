from datetime import timezone as dt_timezone

from rest_framework import serializers


class StrictCharField(serializers.CharField):
    """Only real strings: DRF would otherwise accept 5 as "5"."""

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class StrictEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data).lower()


class NewBookingSerializer(serializers.Serializer):
    slot_id = StrictCharField(max_length=64)
    name = StrictCharField(max_length=255)
    email = StrictEmailField(max_length=320)


def iso_z(dt) -> str:
    """2026-12-10T09:00:00Z style UTC timestamp."""
    return dt.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SlotInputSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=64)
    provider = serializers.CharField(max_length=255)
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class ResetSerializer(serializers.Serializer):
    slots = SlotInputSerializer(many=True, allow_empty=True)

    def validate_slots(self, slots):
        ids = [s["id"] for s in slots]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("duplicate slot id")
        return slots


def slot_to_dict(slot) -> dict:
    return {
        "id": slot.id,
        "provider": slot.provider,
        "start": iso_z(slot.start),
        "end": iso_z(slot.end),
        "available": slot.available,
    }


def booking_to_dict(booking) -> dict:
    return {
        "id": booking.id,
        "slot_id": booking.slot_id,
        "name": booking.name,
        "email": booking.email,
        "status": booking.status,
        "created_at": iso_z(booking.created_at),
    }
