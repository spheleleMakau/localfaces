import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

from .forms import TrainingApplicationForm
from .models import ApplicationEmail

logger = logging.getLogger(__name__)


def send_application_email(notification, request):
    if notification.status == ApplicationEmail.Status.SENT:
        return True

    application = notification.application
    fields = (
        ("Full name", application.full_name),
        ("Email", application.email),
        ("Phone", application.phone),
        ("WhatsApp", application.whatsapp_number),
        ("Age", application.age),
        ("Age category", application.get_age_category_display()),
        ("Gender", application.get_gender_display()),
        ("City", application.city),
        ("Town", application.town),
        ("Current occupation", application.current_occupation),
        ("Shoe size", application.shoe_size),
        ("Pants size", application.pants_size),
        ("Dress size", application.dress_size),
        ("Skirt size", application.skirt_size),
        ("Top size", application.top_size),
        ("Available day", ", ".join(application.get_available_day_labels())),
        ("Available for the full 6 weeks", application.available_full_five_weeks),
        ("Modelling experience", application.has_modelling_experience),
        ("Experience details", application.previous_experience),
        ("Instagram", application.social_handle),
        ("TikTok", application.tiktok_handle),
        ("About", application.about),
        ("Guardian name", application.guardian_name),
        ("Guardian phone", application.guardian_phone),
        ("Privacy consent", application.privacy_consent),
        ("Photo consent", application.photo_consent),
        ("Guardian consent", application.guardian_consent),
    )
    lines = [
        f"Application: {application.application_number}",
        f"Application type: {application.get_kind_display()}",
    ]
    selection = notification.training_selection
    if selection:
        lines.extend([
            f"Training: {'Group course' if selection['training'] == 'course' else 'One-on-one'}",
            f"Training city: {selection['city']}",
        ])
        if selection["training"] == "individual":
            lines.append(f"Hours: {selection['hours']}")
    for label, value in fields:
        if value is True:
            value = "Yes"
        elif value is False:
            value = "No"
        elif value is None or value == "":
            value = "Not provided"
        lines.append(f"{label}: {value}")
    lines.extend([
        "",
        "Sign in as staff to view the application and photographs:",
        request.build_absolute_uri(reverse("admin:camp_application_change", args=[application.pk])),
    ])
    try:
        if not settings.RESEND_API_KEY or not settings.DEFAULT_FROM_EMAIL:
            raise ImproperlyConfigured("RESEND_API_KEY and DEFAULT_FROM_EMAIL must be configured for application emails.")
        message = EmailMessage(
            subject=f"Local Faces application {application.application_number}",
            body="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["info@localfaces.com"],
            headers={"Idempotency-Key": f"application/{application.application_number}"},
        )
        if message.send() != 1:
            raise ValueError("Email backend did not accept the message.")
    except (OSError, ImproperlyConfigured, ValueError):
        logger.exception("Could not email application %s; staff can retry in admin.", application.application_number)
        notification.status = ApplicationEmail.Status.FAILED
        notification.save(update_fields=["status"])
        return False
    notification.status = ApplicationEmail.Status.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at"])
    return True
