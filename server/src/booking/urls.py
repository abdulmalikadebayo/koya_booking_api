from django.urls import re_path

from . import api

urlpatterns = [
    re_path(r"^reset/?$", api.ResetAPIView.as_view(), name="reset"),
    re_path(r"^slots/?$", api.SlotListAPIView.as_view(), name="slots"),
    re_path(r"^bookings/?$", api.BookingListCreateAPIView.as_view(), name="bookings"),
    re_path(
        r"^bookings/(?P<id>[^/]+)/?$",
        api.BookingDetailAPIView.as_view(),
        name="booking-detail",
    ),
]
