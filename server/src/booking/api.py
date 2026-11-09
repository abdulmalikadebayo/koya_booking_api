from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView


class NotFoundAPIView(APIView):
    """Catch-all so unknown routes return the JSON error shape."""

    def handle(self, request, *args, **kwargs):
        raise NotFound("not found")

    get = post = put = patch = delete = handle


class SlotListAPIView(APIView):
    def get(self, request):
        return Response({"slots": []})
