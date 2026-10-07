from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils import timezone

from .models import Application, ApplicationPhoto

class ApplicationPhotoField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            forms.FileInput(
                attrs={"accept": "image/jpeg,image/png"}
            ),
        )
        kwargs.setdefault(
            "validators",
            [FileExtensionValidator(["jpg", "jpeg", "png"])],
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        cleaned_file = super().clean(data, initial)
        if cleaned_file and cleaned_file.size > settings.MAX_APPLICATION_PHOTO_BYTES:
            maximum_mb = settings.MAX_APPLICATION_PHOTO_BYTES // (1024 * 1024)
            raise ValidationError(
                f"Each photograph must be {maximum_mb} MB or smaller."
            )
        return cleaned_file


class ApplicationForm(forms.ModelForm):
    submission_key = forms.UUIDField(widget=forms.HiddenInput)
    gender = forms.ChoiceField(
        label="Gender",
        choices=Application.Gender.choices,
        required=True,
    )
    date_of_birth = forms.DateField(
        label="Date of birth",
        required=True,
        widget=forms.DateInput(
            attrs={"type": "date", "autocomplete": "bday"}
        ),
    )
    whatsapp_number = forms.CharField(
        label="WhatsApp number",
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "tel"}),
    )
    current_occupation = forms.CharField(
        label="What do you currently do?",
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "organization-title"}),
    )
    preferred_days = forms.ChoiceField(
        label="Which day are you available?",
        choices=Application.DAY_CHOICES,
        required=True,
        help_text="Choose one day: Friday, Saturday or Sunday.",
        widget=forms.RadioSelect,
    )
    available_full_five_weeks = forms.ChoiceField(
        label="Available for the full 6 weeks?",
        choices=(("", "Please select"), ("yes", "Yes"), ("no", "No")),
        required=True,
    )
    has_modelling_experience = forms.ChoiceField(
        label="Do you have any modelling experience?",
        choices=(("", "Please select"), ("yes", "Yes"), ("no", "No")),
        required=True,
        widget=forms.Select(
            attrs={"aria-controls": "previous-experience-details"}
        ),
    )
    tiktok_handle = forms.CharField(
        label="TikTok handle",
        max_length=80,
        required=False,
    )
    previous_experience = forms.CharField(
        label="Tell us briefly about your modelling experience",
        required=False,
        help_text="Optional — shown when you answer Yes.",
        widget=forms.Textarea(
            attrs={"rows": 3, "id": "previous-experience-details"}
        ),
    )
    full_length_photo = ApplicationPhotoField(
        label="Picture 1 — Full length",
        help_text="A recent full-length photograph showing your complete outfit. JPG, JPEG or PNG.",
    )
    headshot = ApplicationPhotoField(
        label="Picture 2 — Profile / selfie",
        help_text="A clear, recent profile photo or selfie. JPG, JPEG or PNG.",
    )

    class Meta:
        model = Application
        fields = [
            "full_name",
            "email",
            "phone",
            "whatsapp_number",
            "date_of_birth",
            "age_category",
            "gender",
            "location",
            "current_occupation",
            "preferred_days",
            "available_full_five_weeks",
            "has_modelling_experience",
            "previous_experience",
            "social_handle",
            "tiktok_handle",
            "full_length_photo",
            "headshot",
            "about",
            "guardian_name",
            "guardian_phone",
        ]
        labels = {
            "age_category": "Age category",
            "gender": "Gender",
            "social_handle": "Instagram handle",
            "location": "City, then town",
            "about": "Anything else you'd like us to know?",
        }
        help_texts = {
            "age_category": "Choose the category that matches your calculated age.",
            "location": "Enter your city, followed by your town.",
        }
        widgets = {
            "about": forms.Textarea(attrs={"rows": 4}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "preferred_days": forms.CheckboxSelectMultiple,
            "guardian_phone": forms.TextInput(
                attrs={"autocomplete": "tel"}
            ),
        }

    privacy_consent = forms.BooleanField(
        label=(
            "I agree that Local Faces Agency may use these details to review "
            "and respond to my application."
        )
    )
    photo_consent = forms.BooleanField(
        label=(
            "I confirm these photographs are of me and may be viewed by "
            "Local Faces Agency for this application."
        )
    )
    guardian_consent = forms.BooleanField(
        required=False,
        label=(
            "A parent or guardian has reviewed this application and agrees "
            "to the submission of these details and photographs."
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_photo_paths = []

    def clean(self):
        cleaned_data = super().clean()
        date_of_birth = cleaned_data.get("date_of_birth")
        age = None
        if date_of_birth:
            today = timezone.localdate()
            if date_of_birth > today:
                self.add_error("date_of_birth", "Date of birth cannot be in the future.")
            else:
                age = Application.age_for_date(date_of_birth, today)
                if age > 120:
                    self.add_error(
                        "date_of_birth",
                        "Please enter a valid date of birth.",
                    )
        cleaned_data["age"] = age
        age_category = cleaned_data.get("age_category")
        expected_category = self.age_category_for_age(age)
        if age is not None and expected_category is None:
            self.add_error(
                "date_of_birth",
                "Applicants must be between 5 and 28 years old.",
            )
        elif age_category and expected_category != age_category:
            self.add_error(
                "age_category",
                "Please select the category that matches your age.",
            )
        if age is not None and age < 18:
            if not cleaned_data.get("guardian_name"):
                self.add_error(
                    "guardian_name",
                    "A parent or guardian name is required for applicants under 18.",
                )
            if not cleaned_data.get("guardian_phone"):
                self.add_error(
                    "guardian_phone",
                    "A parent or guardian phone number is required for applicants under 18.",
                )
            if not cleaned_data.get("guardian_consent"):
                self.add_error(
                    "guardian_consent",
                    "Parent or guardian agreement is required for applicants under 18.",
                )
        if cleaned_data.get("has_modelling_experience") is False:
            cleaned_data["previous_experience"] = ""
        return cleaned_data

    @staticmethod
    def age_category_for_age(age):
        if age is None:
            return None
        if 5 <= age <= 12:
            return Application.AgeCategory.KIDS
        if 13 <= age <= 18:
            return Application.AgeCategory.TEENS
        if 19 <= age <= 28:
            return Application.AgeCategory.SENIORS
        return None

    def clean_available_full_five_weeks(self):
        return self.cleaned_data["available_full_five_weeks"] == "yes"

    def clean_preferred_days(self):
        return [self.cleaned_data["preferred_days"]]

    def clean_has_modelling_experience(self):
        return self.cleaned_data["has_modelling_experience"] == "yes"

    def save(self, commit=True):
        application = super().save(commit=False)
        application.submission_key = self.cleaned_data["submission_key"]
        application.age = self.cleaned_data["age"]
        application.available_full_five_weeks = self.cleaned_data[
            "available_full_five_weeks"
        ]
        application.privacy_consent = self.cleaned_data["privacy_consent"]
        application.photo_consent = self.cleaned_data["photo_consent"]
        application.guardian_consent = self.cleaned_data["guardian_consent"]
        if commit:
            application.save()
            self.save_photos(application)
        return application

    def save_photos(self, application):
        photos = [
            ("full_length_photo", ApplicationPhoto.PhotoType.FULL_LENGTH),
            ("headshot", ApplicationPhoto.PhotoType.HEADSHOT),
        ]
        for field_name, photo_type in photos:
            uploaded_file = self.cleaned_data[field_name]
            if uploaded_file is None:
                continue
            photo = ApplicationPhoto(
                application=application,
                photo_type=photo_type,
                image=uploaded_file,
                original_name=uploaded_file.name[:255],
            )
            try:
                photo.save()
            finally:
                if photo.image.name:
                    self.saved_photo_paths.append(photo.image.name)
