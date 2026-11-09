from datetime import datetime, timezone

import pytest

from conftest import make_slot

pytestmark = pytest.mark.django_db

VALID = {"slot_id": "s1", "name": "Ada Obi", "email": "ada@example.com"}


@pytest.fixture(autouse=True)
def one_slot(reset):
    reset(make_slot("s1"))


def post(client, **overrides):
    body = {**VALID, **overrides}
    return client.post("/bookings", body, format="json")


@pytest.mark.parametrize("field", ["slot_id", "name", "email"])
def test_missing_fields_return_400(client, field):
    body = {k: v for k, v in VALID.items() if k != field}
    response = client.post("/bookings", body, format="json")
    assert response.status_code == 400
    assert field in response.json()["error"]


@pytest.mark.parametrize("field", ["slot_id", "name", "email"])
def test_empty_fields_return_400(client, field):
    assert post(client, **{field: ""}).status_code == 400


def test_whitespace_only_name_returns_400(client):
    assert post(client, name="   ").status_code == 400


@pytest.mark.parametrize("email", ["not-an-email", "a@", "@b.com", "a b@c.com"])
def test_invalid_email_returns_400(client, email):
    response = post(client, email=email)
    assert response.status_code == 400
    assert "email" in response.json()["error"]


def test_unknown_slot_returns_404(client):
    response = post(client, slot_id="nope")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}


def test_slot_already_started_returns_400(client, reset):
    reset(make_slot("old", start="2001-01-01T09:00:00Z", end="2001-01-01T09:30:00Z"))
    response = post(client, slot_id="old")
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


def test_slot_starting_now_returns_400(client, monkeypatch):
    monkeypatch.setattr(
        "booking.clock.now",
        lambda: datetime(2099, 12, 10, 9, 0, tzinfo=timezone.utc),
    )
    assert post(client).status_code == 400


def test_name_and_email_trimmed_and_email_lowercased(client):
    response = post(client, name="  Ada Obi ", email=" ADA@Example.com ")
    assert response.status_code == 201
    assert response.json()["name"] == "Ada Obi"
    assert response.json()["email"] == "ada@example.com"


def test_invalid_json_returns_400(client):
    response = client.post("/bookings", data="{bad", content_type="application/json")
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


@pytest.mark.parametrize("body", [[1, 2], "text", 5, None])
def test_non_object_body_returns_400(client, body):
    response = client.post("/bookings", body, format="json")
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


@pytest.mark.parametrize("field", ["slot_id", "name", "email"])
@pytest.mark.parametrize("value", [5, True, ["x"], {"a": 1}])
def test_non_string_fields_return_400(client, field, value):
    assert post(client, **{field: value}).status_code == 400
