from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("django-admin/", admin.site.urls),
    path("", include("camp.urls")),
]
