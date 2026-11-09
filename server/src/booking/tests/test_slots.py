import pytest

from conftest import make_slot

pytestmark = pytest.mark.django_db


def test_reset_replaces_slots_and_returns_200(client, reset):
    reset(make_slot("old"))
    response = reset(
        make_slot("s1"),
        make_slot("s2", start="2099-12-10T10:00:00Z", end="2099-12-10T10:30:00Z"),
    )
    assert response.status_code == 200
    ids = [s["id"] for s in client.get("/slots").json()["slots"]]
    assert ids == ["s1", "s2"]


def test_reset_requires_slots_list(client):
    for body in ({}, {"slots": "x"}, {"slots": [{"id": "s1"}]}):
        response = client.post("/reset", body, format="json")
        assert response.status_code == 400
        assert set(response.json()) == {"error"}


def test_reset_rejects_duplicate_slot_ids(client):
    response = client.post(
        "/reset", {"slots": [make_slot("s1"), make_slot("s1")]}, format="json"
    )
    assert response.status_code == 400


def test_slots_sorted_by_start_with_available_true(client, reset):
    reset(
        make_slot("late", start="2099-12-10T11:00:00Z", end="2099-12-10T11:30:00Z"),
        make_slot("early", start="2099-12-10T09:00:00Z", end="2099-12-10T09:30:00Z"),
    )
    slots = client.get("/slots").json()["slots"]
    assert [s["id"] for s in slots] == ["early", "late"]
    assert slots[0] == {
        "id": "early",
        "provider": "Dr Ade",
        "start": "2099-12-10T09:00:00Z",
        "end": "2099-12-10T09:30:00Z",
        "available": True,
    }


def test_provider_filter_exact_match(client, reset):
    reset(make_slot("a", provider="Dr Ade"), make_slot("b", provider="Dr Ade Jr"))
    slots = client.get("/slots", {"provider": "Dr Ade"}).json()["slots"]
    assert [s["id"] for s in slots] == ["a"]


def test_reset_accepts_past_slots(client, reset):
    response = reset(
        make_slot("past", start="2001-01-01T09:00:00Z", end="2001-01-01T09:30:00Z")
    )
    assert response.status_code == 200
    assert [s["id"] for s in client.get("/slots").json()["slots"]] == ["past"]


def test_reset_clears_bookings_idempotency_and_attempts(client, reset):
    from booking.models import Booking, BookingAttempt, IdempotencyRecord, Slot

    reset(make_slot("s1"))
    slot = Slot.objects.get(pk="s1")
    Booking.objects.create(slot=slot, name="Ada", email="ada@example.com")
    IdempotencyRecord.objects.create(
        key="k", body_hash="h", status_code=201, response={}
    )
    BookingAttempt.objects.create(email="ada@example.com")

    reset(make_slot("s2"))

    assert Booking.objects.count() == 0
    assert IdempotencyRecord.objects.count() == 0
    assert BookingAttempt.objects.count() == 0
    assert list(Slot.objects.values_list("id", flat=True)) == ["s2"]
