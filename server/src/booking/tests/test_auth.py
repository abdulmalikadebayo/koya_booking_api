import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_missing_key_returns_401(anon_client):
    response = anon_client.get("/slots")
    assert response.status_code == 401
    assert set(response.json()) == {"error"}


def test_wrong_key_returns_401():
    response = APIClient(HTTP_X_API_KEY="nope").get("/slots")
    assert response.status_code == 401
    assert set(response.json()) == {"error"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}


def test_unknown_route_without_key_returns_401(anon_client):
    assert anon_client.get("/nope").status_code == 401


def test_wrong_method_returns_json_405(client):
    response = client.post("/slots", {}, format="json")
    assert response.status_code == 405
    assert set(response.json()) == {"error"}


def test_preflight_options_needs_no_key(anon_client):
    response = anon_client.options(
        "/bookings",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-api-key,idempotency-key,content-type",
    )
    assert response.status_code == 200
    allowed = response["Access-Control-Allow-Headers"].lower()
    assert "x-api-key" in allowed
    assert "idempotency-key" in allowed
