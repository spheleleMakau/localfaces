import logging
import mimetypes
import uuid

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.db import DatabaseError, IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ApplicationForm
from .models import Application, ApplicationPhoto
from .sharing import application_share_token, get_shared_application
from .whatsapp import build_application_whatsapp_url

logger = logging.getLogger(__name__)


def apply(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                existing = Application.objects.filter(
                    submission_key=form.cleaned_data["submission_key"]
                ).first()
                if existing:
                    return redirect(
                        build_application_whatsapp_url(existing, request)
                    )
                try:
                    with transaction.atomic():
                        application = form.save()
                except IntegrityError:
                    existing = Application.objects.filter(
                        submission_key=form.cleaned_data["submission_key"]
                    ).first()
                    if existing is None:
                        raise
                    return redirect(
                        build_application_whatsapp_url(existing, request)
                    )
            except (DatabaseError, OSError):
                for image_path in form.saved_photo_paths:
                    try:
                        default_storage.delete(image_path)
                    except OSError:
                        logger.exception(
                            "Could not remove an incomplete applicant photo."
                        )
                logger.exception("Could not save a Local Faces application.")
                form.add_error(
                    None,
                    "We couldn't submit your application. Please try again.",
                )
            else:
                return redirect(
                    build_application_whatsapp_url(application, request)
                )
    else:
        form = ApplicationForm(initial={"submission_key": uuid.uuid4()})
    return render(
        request,
        "camp/apply.html",
        {
            "form": form,
            "photo_max_mb": f"{settings.MAX_APPLICATION_PHOTO_BYTES / (1024 * 1024):g}",
            "max_application_photo_bytes": settings.MAX_APPLICATION_PHOTO_BYTES,
        },
    )


def success(request, token):
    application = get_shared_application(token)
    if application is None:
        raise Http404("This application link is invalid.")
    return render(
        request,
        "camp/success.html",
        {
            "application": application,
            "whatsapp_url": build_application_whatsapp_url(application, request),
        },
    )


@staff_member_required
def dashboard(request):
    applications = Application.objects.prefetch_related("photos").all()
    for application in applications:
        token = application_share_token(application)
        application.review_url = reverse(
            "camp:shared_application", args=[token]
        )
    status_counts = {
        status: Application.objects.filter(status=status).count()
        for status, _label in Application.Status.choices
    }
    return render(
        request,
        "camp/dashboard.html",
        {"applications": applications, "status_counts": status_counts},
    )


def shared_application(request, token):
    application = get_shared_application(token)
    if application is None:
        raise Http404("This application link is invalid.")
    response = render(
        request,
        "camp/shared_application.html",
        {"application": application, "share_token": token},
    )
    response["Cache-Control"] = "private, no-store"
    return response


def shared_photos(request, token):
    application = get_shared_application(token)
    if application is None:
        raise Http404("This application link is invalid.")
    response = render(
        request,
        "camp/shared_photos.html",
        {"application": application, "share_token": token},
    )
    response["Cache-Control"] = "private, no-store"
    return response


def shared_photo(request, token, photo_id):
    application = get_shared_application(token)
    if application is None:
        raise Http404("This photograph link is invalid.")
    photo = get_object_or_404(ApplicationPhoto, pk=photo_id, application=application)
    if not default_storage.exists(photo.image.name):
        raise Http404("This photograph is no longer available.")
    response = FileResponse(
        default_storage.open(photo.image.name, "rb"),
        content_type=mimetypes.guess_type(photo.image.name)[0] or "application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    return response
