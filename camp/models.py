import uuid
from pathlib import Path

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


def application_photo_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"applications/{instance.application.application_number}/{uuid.uuid4().hex}{suffix}"


class Application(models.Model):
    class AgeCategory(models.TextChoices):
        KIDS = "kids", "Kids (5–12)"
        TEENS = "teens", "Teens (13–18)"
        SENIORS = "seniors", "Seniors (19–28)"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class PreferredTime(models.TextChoices):
        MORNING = "morning", "Morning"
        AFTERNOON = "afternoon", "Afternoon"
        EVENING = "evening", "Evening"
        FLEXIBLE = "flexible", "Flexible"

    class InterestArea(models.TextChoices):
        MODELLING = "modelling", "Modelling"
        FASHION = "fashion", "Fashion"
        PHOTOGRAPHY = "photography", "Photography"
        CONFIDENCE = "confidence", "Confidence & self-expression"
        PERSONAL_BRANDING = "personal_branding", "Personal branding"
        COMMUNICATION = "communication", "Communication"
        INDUSTRY_KNOWLEDGE = "industry_knowledge", "Industry knowledge"

    DAY_CHOICES = (
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    )

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWING = "reviewing", "Reviewing"
        SHORTLISTED = "shortlisted", "Shortlisted"
        CONTACTED = "contacted", "Contacted"
        ACCEPTED = "accepted", "Accepted"
        NOT_SELECTED = "not_selected", "Not Selected"

    application_number = models.CharField(
        max_length=24, unique=True, editable=False, db_index=True
    )
    share_token = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    submission_key = models.UUIDField(null=True, blank=True, unique=True)
    full_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    whatsapp_number = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    age_category = models.CharField(
        max_length=12, choices=AgeCategory.choices, blank=True
    )
    gender = models.CharField(max_length=8, choices=Gender.choices, blank=True)
    location = models.CharField(max_length=120)
    current_occupation = models.CharField(max_length=120, blank=True)
    preferred_days = models.JSONField("Available day", default=list, blank=True)
    preferred_time = models.CharField(
        max_length=16, choices=PreferredTime.choices, blank=True
    )
    available_full_five_weeks = models.BooleanField(
        "Available for the full 6 weeks?", null=True, blank=True
    )
    has_modelling_experience = models.BooleanField(
        "Has modelling experience?", null=True, blank=True
    )
    previous_experience = models.TextField(blank=True)
    areas_of_interest = models.JSONField(default=list, blank=True)
    social_handle = models.CharField(max_length=80, blank=True)
    tiktok_handle = models.CharField(max_length=80, blank=True)
    about = models.TextField(blank=True)
    guardian_name = models.CharField(max_length=160, blank=True)
    guardian_phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NEW, db_index=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    privacy_consent = models.BooleanField(default=False)
    photo_consent = models.BooleanField(default=False)
    guardian_consent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]

    @staticmethod
    def age_for_date(date_of_birth, today=None):
        if date_of_birth is None:
            return None
        today = today or timezone.localdate()
        return (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = uuid.uuid4()
        if not self.application_number:
            self.application_number = (
                f"LFA-{timezone.localdate().year}-{uuid.uuid4().hex[:8].upper()}"
            )
        if self.date_of_birth:
            self.age = self.age_for_date(self.date_of_birth)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application_number} — {self.full_name}"

    def get_interest_labels(self):
        labels = dict(self.InterestArea.choices)
        return [labels.get(area, area) for area in self.areas_of_interest]

    def get_available_day_labels(self):
        labels = dict(self.DAY_CHOICES)
        return [labels.get(day, day) for day in self.preferred_days]


class ApplicationPhoto(models.Model):
    class PhotoType(models.TextChoices):
        HEADSHOT = "headshot", "Profile / selfie"
        FULL_LENGTH = "full_length", "Full-length"
        SHOULDER_UP = "shoulder_up", "Shoulder-up"
        ADDITIONAL = "additional", "Additional"
        OTHER = "other", "Other"

    application = models.ForeignKey(
        Application, related_name="photos", on_delete=models.CASCADE
    )
    photo_type = models.CharField(
        max_length=16, choices=PhotoType.choices, default=PhotoType.OTHER
    )
    image = models.ImageField(
        upload_to=application_photo_path,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.application.application_number} — {self.original_name}"
