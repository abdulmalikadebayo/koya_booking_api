import uuid

import pytest

from conftest import make_slot

pytestmark = pytest.mark.django_db

BOOKING_FIELDS = {"id", "slot_id", "name", "email", "status", "created_at"}


def test_book_returns_201_with_confirmed_booking(reset, book):
    reset(make_slot("s1"))
    response = book()
    assert response.status_code == 201
    body = response.json()
    assert set(body) == BOOKING_FIELDS
    assert body["status"] == "confirmed"
    assert body["slot_id"] == "s1"
    assert body["name"] == "Ada Obi"
    assert body["email"] == "ada@example.com"
    assert str(uuid.UUID(body["id"])) == body["id"]
    assert body["created_at"].endswith("Z")


def test_booked_slot_shows_available_false(client, reset, book):
    reset(
        make_slot("s1"),
        make_slot("s2", start="2099-12-10T10:00:00Z", end="2099-12-10T10:30:00Z"),
    )
    book("s1")
    slots = {s["id"]: s["available"] for s in client.get("/slots").json()["slots"]}
    assert slots == {"s1": False, "s2": True}


def test_get_booking_by_id_returns_200(client, reset, book):
    reset(make_slot("s1"))
    created = book().json()
    response = client.get(f"/bookings/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_booking_returns_404_error_shape(client):
    response = client.get("/bookings/does-not-exist")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}
