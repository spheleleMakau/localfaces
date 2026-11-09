import logging
import mimetypes
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import DatabaseError, IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .forms import ModelApplicationForm
from .models import Application, ApplicationEmail, ApplicationPhoto
from .notifications import send_application_email
from .sharing import application_share_token, get_shared_application
from .whatsapp import build_application_whatsapp_url

logger = logging.getLogger(__name__)

def model_application_redirect(request, application):
    notification = ApplicationEmail.objects.filter(application=application).first()
    if notification and notification.status != ApplicationEmail.Status.SENT:
        return redirect("camp:success", token=application.share_token)
    return redirect(build_application_whatsapp_url(application, request))


@require_GET
def training_details(request):
    return render(request, "camp/apply.html")


def apply(request):
    if request.method == "POST":
        form = ModelApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                existing = Application.objects.filter(
                    submission_key=form.cleaned_data["submission_key"]
                ).first()
                if existing:
                    if existing.kind != Application.Kind.MODEL:
                        form.add_error(None, "This submission has already been used. Please start a new application.")
                        form.add_error("submission_key", "Reload the page for a new submission.")
                        return render(request, "agency/join.html", {"form": form, "show_model": True})
                    return model_application_redirect(request, existing)
                try:
                    with transaction.atomic():
                        application = form.save()
                        notification = ApplicationEmail.objects.create(application=application)
                except IntegrityError:
                    existing = Application.objects.filter(
                        submission_key=form.cleaned_data["submission_key"]
                    ).first()
                    if existing is None:
                        raise
                    if existing.kind != Application.Kind.MODEL:
                        form.add_error(None, "This submission has already been used. Please start a new application.")
                        form.add_error("submission_key", "Reload the page for a new submission.")
                        return render(request, "agency/join.html", {"form": form, "show_model": True})
                    return model_application_redirect(request, existing)
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
                    "We couldn't save your application because of a technical problem. Please try again, or contact info@localfaces.co.za if the problem continues.",
                )
            else:
                if not send_application_email(notification, request):
                    return redirect("camp:success", token=application.share_token)
                return redirect(
                    build_application_whatsapp_url(application, request)
                )
    else:
        form = ModelApplicationForm(initial={"submission_key": uuid.uuid4()})
    return render(
        request,
        "agency/join.html",
        {
            "form": form,
            "show_model": request.method == "POST",
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
