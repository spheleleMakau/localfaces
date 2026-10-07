import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from .models import Application


def _whatsapp_number():
    number = settings.LOCAL_FACES_WHATSAPP_NUMBER
    if not re.fullmatch(r"[1-9]\d{7,14}", number):
        raise ImproperlyConfigured(
            "LOCAL_FACES_WHATSAPP_NUMBER must use international digits only, "
            "for example 27671012841."
        )
    return number


def build_application_whatsapp_url(application: Application, request):
    token = application.share_token
    application_url = request.build_absolute_uri(
        reverse("camp:shared_application", args=[token])
    )
    photos_url = request.build_absolute_uri(
        reverse("camp:shared_photos", args=[token])
    )
    date_of_birth = (
        application.date_of_birth.strftime("%d %B %Y")
        if application.date_of_birth
        else "Not provided"
    )
    lines = [
        "NEW LOCAL FACES SUMMER CAMP APPLICATION",
        "",
        f"Application: {application.application_number}",
        f"Applicant: {application.full_name}",
        f"Date of Birth: {date_of_birth}",
        f"Age: {application.age if application.age is not None else 'Not provided'}",
        f"Location: {application.location}",
        f"Phone: {application.phone}",
        f"Email: {application.email}",
        f"WhatsApp: {application.whatsapp_number or 'Not provided'}",
        f"Currently: {application.current_occupation or 'Not provided'}",
        "Available for Full 5 Weeks: "
        + (
            "Yes"
            if application.available_full_five_weeks is True
            else "No"
            if application.available_full_five_weeks is False
            else "Not provided"
        ),
        "Experience: "
        + (application.previous_experience.strip() or "No previous experience provided"),
        f"Instagram: {application.social_handle or 'Not provided'}",
        "",
        f"PHOTOS: {photos_url}",
        f"FULL APPLICATION: {application_url}",
    ]
    message = "\n".join(lines)
    return f"https://wa.me/{_whatsapp_number()}?{urlencode({'text': message})}"
