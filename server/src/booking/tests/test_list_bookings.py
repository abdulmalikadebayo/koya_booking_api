import pytest

from conftest import make_slot

pytestmark = pytest.mark.django_db


def slots(n):
    return [
        make_slot(
            f"s{i}",
            start=f"2099-12-10T{9 + i // 60:02d}:{i % 60:02d}:00Z",
            end=f"2099-12-10T{9 + i // 60:02d}:{i % 60:02d}:30Z",
        )
        for i in range(n)
    ]


@pytest.fixture
def booked(reset):
    """Create n bookings for one email directly in the database (the API would
    rate limit more than 5 per minute); returns the ids in creation order."""

    def _booked(n, email="ada@example.com"):
        from datetime import datetime, timedelta, timezone

        from booking.models import Booking, Slot

        reset(*slots(n))
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return [
            Booking.objects.create(
                slot=Slot.objects.get(pk=f"s{i}"),
                name="Ada",
                email=email,
                created_at=base + timedelta(minutes=i),
            ).id
            for i in range(n)
        ]

    return _booked


def list_bookings(client, **params):
    return client.get("/bookings", params)


def test_lists_only_that_email_case_insensitive(client, reset, book):
    reset(*slots(3))
    book("s0", email="ada@example.com")
    book("s1", email="bola@example.com")
    response = list_bookings(client, email="ADA@Example.com")
    assert response.status_code == 200
    assert [b["email"] for b in response.json()["bookings"]] == ["ada@example.com"]


def test_oldest_first(client, booked):
    ids = booked(5)
    got = [
        b["id"]
        for b in list_bookings(client, email="ada@example.com").json()["bookings"]
    ]
    assert got == ids


def test_paging_visits_every_booking_exactly_once(client, booked):
    ids = booked(25)
    seen, cursor, pages = [], None, 0
    while True:
        params = {"email": "ada@example.com", "limit": 10}
        if cursor:
            params["cursor"] = cursor
        body = list_bookings(client, **params).json()
        seen += [b["id"] for b in body["bookings"]]
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert pages == 3
    assert seen == ids


def test_exact_multiple_of_limit_ends_with_null_cursor(client, booked):
    booked(10)
    body = list_bookings(client, email="ada@example.com", limit=10).json()
    assert len(body["bookings"]) == 10
    assert body["next_cursor"] is None


def test_includes_cancelled_bookings(client, booked):
    ids = booked(2)
    client.delete(f"/bookings/{ids[0]}")
    got = list_bookings(client, email="ada@example.com").json()["bookings"]
    assert [b["status"] for b in got] == ["cancelled", "confirmed"]


def test_unknown_email_returns_empty_page(client):
    response = list_bookings(client, email="nobody@example.com")
    assert response.status_code == 200
    assert response.json() == {"bookings": [], "next_cursor": None}


@pytest.mark.parametrize("limit", ["0", "51", "abc", "-1", "", "1.5"])
def test_bad_limit_returns_400(client, limit):
    response = list_bookings(client, email="ada@example.com", limit=limit)
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


@pytest.mark.parametrize("limit", ["1", "50"])
def test_limit_bounds_are_allowed(client, limit):
    assert (
        list_bookings(client, email="ada@example.com", limit=limit).status_code == 200
    )


@pytest.mark.parametrize("params", [{}, {"email": ""}, {"email": "   "}])
def test_missing_email_returns_400(client, params):
    assert list_bookings(client, **params).status_code == 400


@pytest.mark.parametrize("cursor", ["garbage", "e30", "bm90LWpzb24"])
def test_tampered_cursor_returns_400(client, booked, cursor):
    booked(2)
    response = list_bookings(client, email="ada@example.com", cursor=cursor)
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


def test_default_limit_is_10(client, booked):
    booked(12)
    body = list_bookings(client, email="ada@example.com").json()
    assert len(body["bookings"]) == 10
    assert body["next_cursor"] is not None
