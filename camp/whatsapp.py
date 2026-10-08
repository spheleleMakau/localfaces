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
            "for example 27681946795."
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
    lines = [
        "NEW LOCAL FACES SUMMER CAMP APPLICATION",
        "",
        f"Application: {application.application_number}",
        f"Applicant: {application.full_name}",
        f"Age: {application.age if application.age is not None else 'Not provided'}",
        f"Age category: {application.get_age_category_display() or 'Not provided'}",
        f"Gender: {application.get_gender_display() or 'Not provided'}",
        f"City: {application.city}",
        f"Town: {application.town or 'Not provided'}",
        f"Phone: {application.phone}",
        f"Email: {application.email}",
        f"WhatsApp: {application.whatsapp_number or 'Not provided'}",
        f"Currently: {application.current_occupation or 'Not provided'}",
        "Available day: "
        + (", ".join(application.get_available_day_labels()) or "Not provided"),
        "Available for Full 6 Weeks: "
        + (
            "Yes"
            if application.available_full_five_weeks is True
            else "No"
            if application.available_full_five_weeks is False
            else "Not provided"
        ),
        "Modelling experience: "
        + (
            "Yes"
            if application.has_modelling_experience is True
            else "No"
            if application.has_modelling_experience is False
            else "Not provided"
        ),
        "Experience: "
        + (application.previous_experience.strip() or "No previous experience provided"),
        f"Instagram: {application.social_handle or 'Not provided'}",
        f"TikTok: {application.tiktok_handle or 'Not provided'}",
        "",
        f"PHOTOS: {photos_url}",
        f"FULL APPLICATION: {application_url}",
    ]
    message = "\n".join(lines)
    return f"https://wa.me/{_whatsapp_number()}?{urlencode({'text': message})}"
