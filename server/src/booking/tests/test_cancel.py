import pytest

from conftest import make_slot

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def one_slot(reset):
    reset(make_slot("s1"))


def test_cancel_sets_status_and_frees_slot(client, book):
    created = book().json()
    response = client.delete(f"/bookings/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["id"] == created["id"]
    assert client.get("/slots").json()["slots"][0]["available"] is True
    assert client.get(f"/bookings/{created['id']}").json()["status"] == "cancelled"


def test_cancelled_slot_can_be_booked_again(client, book):
    first = book().json()
    client.delete(f"/bookings/{first['id']}")
    second = book(email="bola@example.com")
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]


def test_cancel_twice_returns_409(client, book):
    created = book().json()
    client.delete(f"/bookings/{created['id']}")
    response = client.delete(f"/bookings/{created['id']}")
    assert response.status_code == 409
    assert set(response.json()) == {"error"}


def test_cancel_unknown_returns_404(client):
    response = client.delete("/bookings/nope")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}
