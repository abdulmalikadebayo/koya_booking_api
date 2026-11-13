from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection
from rest_framework.test import APIClient

from conftest import TEST_KEY, make_slot


def key(value):
    return {"HTTP_IDEMPOTENCY_KEY": value}


@pytest.mark.django_db
class TestIdempotency:
    @pytest.fixture(autouse=True)
    def one_slot(self, reset):
        reset(make_slot("s1"))

    def test_same_key_same_body_replays_same_booking_id_and_status(self, book):
        first = book(**key("k1"))
        second = book(**key("k1"))
        assert first.status_code == second.status_code == 201
        assert first.json() == second.json()

    def test_replay_does_not_create_second_booking(self, book):
        from booking.models import Booking

        book(**key("k1"))
        book(**key("k1"))
        assert Booking.objects.count() == 1

    def test_equivalent_body_after_trim_and_lowercase_replays(self, book):
        first = book(**key("k1"))
        second = book(email=" ADA@example.com ", name=" Ada Obi", **key("k1"))
        assert second.status_code == 201
        assert second.json()["id"] == first.json()["id"]

    def test_same_key_different_body_returns_422(self, book):
        book(**key("k1"))
        response = book(email="bola@example.com", **key("k1"))
        assert response.status_code == 422
        assert set(response.json()) == {"error"}

    def test_failed_request_is_not_stored(self, client, book):
        taken = book(email="bola@example.com").json()
        assert book(**key("k1")).status_code == 409
        client.delete(f"/bookings/{taken['id']}")
        retry = book(**key("k1"))
        assert retry.status_code == 201

    def test_no_key_means_no_idempotency(self, book):
        assert book().status_code == 201
        assert book().status_code == 409

    def test_different_keys_are_independent(self, book):
        assert book(**key("a")).status_code == 201
        assert book(**key("b")).status_code == 409


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_key_creates_one_booking(reset):
    from booking.models import Booking

    reset(make_slot("s1"))

    def attempt(_):
        try:
            c = APIClient(HTTP_X_API_KEY=TEST_KEY)
            r = c.post(
                "/bookings",
                {"slot_id": "s1", "name": "Ada", "email": "ada@example.com"},
                format="json",
                HTTP_IDEMPOTENCY_KEY="same",
            )
            return r.status_code, r.json().get("id")
        finally:
            connection.close()

    # 5 requests: the most one email may send in a minute
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(attempt, range(5)))

    assert {code for code, _ in results} == {201}
    assert len({booking_id for _, booking_id in results}) == 1
    assert Booking.objects.count() == 1
