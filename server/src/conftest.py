import pytest
from rest_framework.test import APIClient

TEST_KEY = "test-key"


@pytest.fixture(autouse=True)
def api_keys(settings):
    settings.API_KEYS = [TEST_KEY]
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]


@pytest.fixture
def client():
    """API client that sends a valid X-API-Key."""
    return APIClient(HTTP_X_API_KEY=TEST_KEY)


@pytest.fixture
def anon_client():
    """API client that sends no key."""
    return APIClient()


def make_slot(
    id="s1",
    provider="Dr Ade",
    start="2099-12-10T09:00:00Z",
    end="2099-12-10T09:30:00Z",
):
    return {"id": id, "provider": provider, "start": start, "end": end}


@pytest.fixture
def reset(client):
    """Replace all slots through the API; returns the response."""

    def _reset(*slots):
        return client.post("/reset", {"slots": list(slots)}, format="json")

    return _reset
