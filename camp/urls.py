from django.urls import path

from . import views

app_name = "camp"

urlpatterns = [
    path("", views.apply, name="apply"),
    path("apply/", views.apply, name="apply_form"),
    path(
        "application-received/<uuid:token>/",
        views.success,
        name="success",
    ),
    path("agency/applications/", views.dashboard, name="dashboard"),
    path(
        "application/<uuid:token>/",
        views.shared_application,
        name="shared_application",
    ),
    path(
        "application/<uuid:token>/photos/",
        views.shared_photos,
        name="shared_photos",
    ),
    path(
        "application/<uuid:token>/photos/<int:photo_id>/",
        views.shared_photo,
        name="shared_photo",
    ),
]
