from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _first_message(data) -> str:
    """Flatten DRF error data (str, list or dict) to its first message."""
    if isinstance(data, dict):
        if "detail" in data:
            data = data["detail"]
        elif data:
            field, value = next(iter(data.items()))
            return f"{field}: {_first_message(value)}"
        else:
            data = "error"
    if isinstance(data, (list, tuple)):
        data = data[0] if data else "error"
        if isinstance(data, (dict, list, tuple)):
            return _first_message(data)
    return str(data)


def exception_handler(exc, context):
    """Every error leaves the API as {"error": "<message>"}."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return Response({"error": "internal server error"}, status=500)
    response.data = {"error": _first_message(response.data)}
    return response
