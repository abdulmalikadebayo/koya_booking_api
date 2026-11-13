from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import connection
from rest_framework.test import APIClient

from conftest import TEST_KEY, make_slot


def attempt(client, email="ada@example.com", slot_id="s1"):
    return client.post(
        "/bookings",
        {"slot_id": slot_id, "name": "Ada", "email": email},
        format="json",
    )


@pytest.mark.django_db
class TestRateLimit:
    @pytest.fixture(autouse=True)
    def one_slot(self, reset):
        reset(make_slot("s1"))

    def test_sixth_attempt_in_a_minute_returns_429(self, client):
        # failed attempts count too: 1 success, 4 conflicts, then the limit
        codes = [attempt(client).status_code for _ in range(5)]
        assert codes == [201, 409, 409, 409, 409]
        response = attempt(client)
        assert response.status_code == 429
        assert set(response.json()) == {"error"}

    def test_unknown_slot_attempts_count(self, client):
        for _ in range(5):
            assert attempt(client, slot_id="nope").status_code == 404
        assert attempt(client, slot_id="nope").status_code == 429

    def test_retry_after_is_integer_of_at_least_1(self, client):
        for _ in range(5):
            attempt(client)
        response = attempt(client)
        retry_after = response["Retry-After"]
        assert retry_after.isdigit()
        assert 1 <= int(retry_after) <= 60

    def test_other_email_not_affected(self, client):
        for _ in range(6):
            attempt(client)
        assert attempt(client, email="bola@example.com").status_code == 409

    def test_email_normalised_before_counting(self, client):
        for email in ["ada@example.com", " ADA@example.com ", "Ada@Example.com"] * 2:
            last = attempt(client, email=email)
        assert last.status_code == 429

    def test_window_expires(self, client, monkeypatch):
        from booking import clock

        for _ in range(5):
            attempt(client)
        assert attempt(client).status_code == 429
        later = clock.now() + timedelta(seconds=61)
        monkeypatch.setattr("booking.clock.now", lambda: later)
        assert attempt(client).status_code == 409

    def test_invalid_email_attempts_not_counted(self, client):
        for _ in range(10):
            assert attempt(client, email="not-an-email").status_code == 400
        assert attempt(client, email="ada@example.com").status_code == 201

    def test_missing_email_attempts_not_counted(self, client):
        for _ in range(10):
            response = client.post(
                "/bookings", {"slot_id": "s1", "name": "A"}, format="json"
            )
            assert response.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_cannot_exceed_limit(reset):
    reset(make_slot("s1"))

    def go(_):
        try:
            c = APIClient(HTTP_X_API_KEY=TEST_KEY)
            return attempt(c).status_code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(go, range(12)))

    assert codes.count(429) == 7
    assert len(codes) - codes.count(429) == 5
