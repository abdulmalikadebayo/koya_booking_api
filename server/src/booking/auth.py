from django.conf import settings

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ApiKeyUser:
    is_authenticated = True


class ApiKeyAuthentication(BaseAuthentication):
    """Every request must send a valid X-API-Key header."""

    def authenticate(self, request):
        key = request.headers.get("X-API-Key")
        if not key or key not in settings.API_KEYS:
            raise AuthenticationFailed("invalid or missing API key")
        return ApiKeyUser(), key

    def authenticate_header(self, request):
        return "X-API-Key"
