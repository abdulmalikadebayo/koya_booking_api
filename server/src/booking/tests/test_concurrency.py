from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection
from rest_framework.test import APIClient

from conftest import TEST_KEY, make_slot


@pytest.mark.django_db
def test_slot_already_booked_returns_409(reset, book):
    reset(make_slot("s1"))
    assert book().status_code == 201
    response = book(email="bola@example.com")
    assert response.status_code == 409
    assert set(response.json()) == {"error"}


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_one_winner(reset):
    from booking.models import Booking

    reset(make_slot("s1"))

    def attempt(i):
        try:
            c = APIClient(HTTP_X_API_KEY=TEST_KEY)
            return c.post(
                "/bookings",
                {"slot_id": "s1", "name": "P", "email": f"p{i}@example.com"},
                format="json",
            ).status_code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(attempt, range(20)))

    assert sorted(codes) == [201] + [409] * 19
    assert Booking.objects.filter(slot_id="s1", status="confirmed").count() == 1
