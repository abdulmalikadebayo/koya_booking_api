"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path, re_path

from booking.api import NotFoundAPIView

# No admin site: every request must carry the API key, and slots only arrive
# through POST /reset.
urlpatterns = [
    path("", include("booking.urls")),
    # Anything else: JSON 404 (after the API key check)
    re_path(r"^.*$", NotFoundAPIView.as_view()),
]
