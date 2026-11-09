from django.urls import re_path

from . import api

urlpatterns = [
    re_path(r"^slots/?$", api.SlotListAPIView.as_view(), name="slots"),
]
