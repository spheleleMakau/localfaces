from django import forms
from django.core.validators import FileExtensionValidator

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


class ApplicationForm(forms.ModelForm):
    submission_key = forms.UUIDField(widget=forms.HiddenInput)
    gender = forms.ChoiceField(
        label="Gender",
        choices=Application.Gender.choices,
        required=True,
    )
    age = forms.IntegerField(
        label="Age",
        min_value=5,
        max_value=28,
        required=True,
        widget=forms.NumberInput(attrs={"min": 5, "max": 28, "step": 1}),
        error_messages={
            "min_value": "Applicants must be between 5 and 28 years old.",
            "max_value": "Applicants must be between 5 and 28 years old.",
        },
    )
    city = forms.CharField(label="City", max_length=120, required=True)
    town = forms.CharField(label="Town", max_length=120, required=True)
    whatsapp_number = forms.CharField(
        label="WhatsApp number",
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "numeric", "maxlength": 10, "minlength": 10, "pattern": "[0-9]{10}", "data-digits-only": "", "placeholder": "0681946795"}),
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
            "age",
            "age_category",
            "gender",
            "city",
            "town",
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
            "about": "Anything else you'd like us to know?",
        }
        help_texts = {
            "age_category": "Choose the category that matches your age.",
        }
        widgets = {
            "about": forms.Textarea(attrs={"rows": 4}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "numeric", "maxlength": 10, "minlength": 10, "pattern": "[0-9]{10}", "data-digits-only": "", "placeholder": "0681946795"}),
            "preferred_days": forms.CheckboxSelectMultiple,
            "guardian_phone": forms.TextInput(
                attrs={"autocomplete": "tel", "inputmode": "numeric", "maxlength": 10, "minlength": 10, "pattern": "[0-9]{10}", "data-digits-only": "", "placeholder": "0681946795"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_photo_paths = []

    def _clean_ten_digits(self, name, label):
        value = (self.cleaned_data.get(name) or "").strip()
        if value and not (value.isascii() and value.isdigit() and len(value) == 10):
            raise forms.ValidationError(f"{label} must be exactly 10 digits (numbers only), e.g. 0681946795.")
        return value

    def clean_phone(self):
        return self._clean_ten_digits("phone", "Phone number")

    def clean_whatsapp_number(self):
        return self._clean_ten_digits("whatsapp_number", "WhatsApp number")

    def clean_guardian_phone(self):
        return self._clean_ten_digits("guardian_phone", "Guardian phone number")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        domain = email.rsplit("@", 1)[-1]
        if "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise forms.ValidationError("Enter a valid email address, e.g. name@example.com.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        age = cleaned_data.get("age")
        age_category = cleaned_data.get("age_category")
        expected_category = self.age_category_for_age(age)
        if age is not None and expected_category is None:
            self.add_error(
                "age",
                "Applicants must be between 5 and 28 years old.",
            )
        elif age_category and expected_category != age_category:
            self.add_error(
                "age_category",
                f"Your age ({age}) does not match the selected category. Please choose {Application.AgeCategory(expected_category).label}.",
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
        application.available_full_five_weeks = self.cleaned_data.get("available_full_five_weeks")
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


class SizedApplicationForm(ApplicationForm):
    shoe_size = forms.CharField(label="Shoe size", max_length=30)
    pants_size = forms.CharField(label="Pants size", max_length=30)
    dress_size = forms.CharField(label="Dress size", max_length=30, required=False)
    skirt_size = forms.CharField(label="Skirt size", max_length=30, required=False)
    top_size = forms.CharField(label="Top size", max_length=30)

    class Meta(ApplicationForm.Meta):
        fields = ApplicationForm.Meta.fields + [
            "shoe_size", "pants_size", "dress_size", "skirt_size", "top_size"
        ]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("gender") == Application.Gender.FEMALE:
            for name in ("dress_size", "skirt_size"):
                if not cleaned_data.get(name):
                    self.add_error(name, "This field is required.")
        else:
            cleaned_data["dress_size"] = ""
            cleaned_data["skirt_size"] = ""
        return cleaned_data


class TalentStyleApplicationForm(SizedApplicationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("age_category", "preferred_days", "available_full_five_weeks"):
            self.fields.pop(field)


class ModelApplicationForm(TalentStyleApplicationForm):
    def save(self, commit=True):
        application = super().save(commit=False)
        application.kind = Application.Kind.MODEL
        if commit:
            application.save()
            self.save_photos(application)
        return application


class TrainingApplicationForm(SizedApplicationForm):
    pass


class IndividualTrainingApplicationForm(TalentStyleApplicationForm):
    pass
