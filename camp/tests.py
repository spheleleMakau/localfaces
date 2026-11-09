from io import BytesIO
import json
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.core.mail import EmailMessage
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import ApplicationForm
from .email_backend import ResendEmailBackend
from .models import Application, ApplicationEmail, ApplicationPhoto
from .sharing import application_share_token
from .whatsapp import build_application_whatsapp_url


def make_png():
    output = BytesIO()
    Image.new("RGB", (2, 2), color="teal").save(output, format="PNG")
    return output.getvalue()


@override_settings(RESEND_API_KEY="test-key")
class ResendEmailBackendTests(TestCase):
    @patch("camp.email_backend.urlopen")
    def test_sends_application_to_resend_with_idempotency_key(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"id":"email-id"}'
        message = EmailMessage(
            "Application", "Application details", "info@localfaces.co.za",
            ["info@localfaces.com"], headers={"Idempotency-Key": "application/LFA-test"},
        )
        self.assertEqual(ResendEmailBackend().send_messages([message]), 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(request.get_header("Idempotency-key"), "application/LFA-test")
        self.assertEqual(json.loads(request.data), {
            "from": "info@localfaces.co.za", "to": ["info@localfaces.com"],
            "subject": "Application", "text": "Application details",
        })

    @patch("camp.email_backend.urlopen")
    def test_response_without_email_id_is_not_success(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{}'
        with self.assertRaises(ValueError):
            ResendEmailBackend().send_messages([
                EmailMessage("Application", "Details", "info@localfaces.co.za", ["info@localfaces.co.za"])
            ])


class CampPagesTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_training_urls_show_details_without_accepting_applications(self):
        for url in (reverse("camp:apply"), reverse("camp:apply_form")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Training details")
                self.assertContains(response, reverse("training_shop"))
                self.assertNotContains(response, "data-application-form")
                self.assertNotContains(response, 'name="submission_key"')
                self.assertEqual(self.client.post(url, {}).status_code, 405)
                self.assertContains(
                    response,
                    "agency/img/logo-light.png",
                    count=2,
                )
                self.assertNotContains(response, "camp/img/logo")

    def test_other_public_pages_have_been_removed(self):
        self.assertEqual(self.client.get("/faq/").status_code, 404)
        self.assertEqual(self.client.get("/home/").status_code, 404)

    def test_age_category_ranges_include_age_18_with_teens(self):
        category_by_age = {
            4: None,
            5: Application.AgeCategory.KIDS,
            12: Application.AgeCategory.KIDS,
            13: Application.AgeCategory.TEENS,
            18: Application.AgeCategory.TEENS,
            19: Application.AgeCategory.SENIORS,
            28: Application.AgeCategory.SENIORS,
            29: None,
        }
        for age, expected_category in category_by_age.items():
            with self.subTest(age=age):
                self.assertEqual(
                    ApplicationForm.age_category_for_age(age),
                    expected_category,
                )

    def test_model_form_retains_application_fields_and_two_required_photo_slots(self):
        response = self.client.get(reverse("join"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="age"')
        self.assertNotContains(response, 'name="date_of_birth"')
        self.assertNotContains(response, "Select all days that suit you.")
        self.assertNotContains(response, "Monday")
        self.assertNotContains(response, "Areas of interest")
        self.assertNotContains(response, "Select all areas you are interested in.")
        self.assertNotContains(response, 'name="preferred_days"')
        self.assertNotContains(response, 'name="available_full_five_weeks"')
        self.assertContains(response, 'type="radio"')
        self.assertNotContains(response, 'name="areas_of_interest"')
        self.assertNotContains(response, "Preferred time")
        self.assertNotContains(response, 'name="preferred_time"')
        self.assertContains(response, "MODEL APPLICATION")
        self.assertNotContains(response, 'name="age_category"')
        self.assertContains(response, "Gender")
        self.assertContains(response, "Male")
        self.assertContains(response, "Female")
        self.assertContains(response, 'name="gender"')
        self.assertTrue(response.context["form"]["gender"].field.required)
        self.assertTrue(response.context["form"]["age"].field.required)
        self.assertTrue(response.context["form"]["city"].field.required)
        self.assertTrue(response.context["form"]["town"].field.required)
        self.assertContains(response, "Do you have any modelling experience?")
        self.assertContains(response, "Instagram handle")
        self.assertContains(response, "TikTok handle")
        self.assertContains(response, 'name="city"')
        self.assertContains(response, 'name="town"')
        self.assertContains(response, "Submit application")
        self.assertContains(response, 'name="headshot"')
        self.assertContains(response, "JPG, JPEG or PNG")
        self.assertNotContains(response, "No per-photo size limit")
        self.assertContains(response, 'name="full_length_photo"')
        self.assertNotContains(response, 'name="additional_photo_1"')
        self.assertNotContains(response, "OPTIONAL")
        self.assertContains(response, "Picture 1 — Full length")
        self.assertContains(response, "Picture 2 — Profile / selfie")
        self.assertNotContains(response, "application/shoulder_up_photo")

    def test_dashboard_requires_staff_login(self):
        response = self.client.get(reverse("camp:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_private_dashboard_is_available_to_staff(self):
        staff = get_user_model().objects.create_superuser(
            username="agency",
            email="agency@example.com",
            password="StrongTestPassword123!",
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("camp:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No applications yet")

    def test_dashboard_contains_secure_application_and_admin_links(self):
        staff = get_user_model().objects.create_superuser(
            username="reviewer",
            email="reviewer@example.com",
            password="StrongTestPassword123!",
        )
        application = Application.objects.create(
            full_name="Jamie Applicant",
            email="jamie@example.com",
            phone="0123456789",
            city="Pretoria",
            privacy_consent=True,
            photo_consent=True,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("camp:dashboard"))
        self.assertContains(response, "View application")
        self.assertContains(
            response,
            reverse("admin:camp_application_change", args=[application.pk]),
        )
        self.assertContains(response, str(application.share_token))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RESEND_API_KEY="test-key",
    DEFAULT_FROM_EMAIL="sender@example.com",
)
class ApplicationSubmissionTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=Path(self.media_directory.name)
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def submission_data(self, **overrides):
        image_bytes = make_png()
        data = {
            "submission_key": str(uuid4()),
            "full_name": "Jordan Example",
            "email": "jordan@example.com",
            "phone": "0123456789",
            "whatsapp_number": "0671234567",
            "age": "20",
            "age_category": "seniors",
            "gender": "female",
            "shoe_size": "6",
            "pants_size": "32",
            "dress_size": "10",
            "skirt_size": "10",
            "top_size": "M",
            "city": "Cape Town",
            "town": "Sea Point",
            "current_occupation": "Student",
            "preferred_days": "Friday",
            "available_full_five_weeks": "yes",
            "has_modelling_experience": "yes",
            "previous_experience": "Community theatre",
            "social_handle": "@jordan",
            "tiktok_handle": "@jordanstudio",
            "about": "I enjoy creative projects.",
            "privacy_consent": "on",
            "photo_consent": "on",
            "headshot": SimpleUploadedFile(
                "headshot.png", image_bytes, content_type="image/png"
            ),
            "full_length_photo": SimpleUploadedFile(
                "full-body.png", image_bytes, content_type="image/png"
            ),
        }
        data.update(overrides)
        return data

    def test_model_application_saves_sizes_and_uses_whatsapp_flow(self):
        response = self.client.post(reverse("join"), self.submission_data(
            shoe_size="6", pants_size="32", dress_size="10", skirt_size="10", top_size="M",
        ))
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get()
        self.assertEqual(application.kind, Application.Kind.MODEL)
        self.assertEqual(application.dress_size, "10")
        self.assertEqual(application.skirt_size, "10")
        self.assertEqual(application.photos.count(), 2)
        message = parse_qs(urlsplit(response["Location"]).query)["text"][0]
        self.assertIn("MODEL APPLICATION", message)
        self.assertIn("Shoe size: 6", message)
        self.assertContains(self.client.get(reverse("camp:shared_application", args=[application.share_token])), "Dress size")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["info@localfaces.com"])
        self.assertIn("Full name: Jordan Example", email.body)
        self.assertIn("About: I enjoy creative projects.", email.body)
        self.assertIn("Shoe size: 6", email.body)
        self.assertIn(reverse("admin:camp_application_change", args=[application.pk]), email.body)
        self.assertNotIn(str(application.share_token), email.body)
        self.assertEqual(email.attachments, [])
        self.assertEqual(application.notification_email.status, ApplicationEmail.Status.SENT)
        self.assertEqual(self.client.get(reverse("admin:camp_application_change", args=[application.pk])).status_code, 302)

    @override_settings(RESEND_API_KEY="")
    def test_email_failure_keeps_application_and_staff_can_retry(self):
        response = self.client.post(reverse("join"), self.submission_data())
        application = Application.objects.get()
        self.assertRedirects(response, reverse("camp:success", args=[application.share_token]), fetch_redirect_response=False)
        self.assertNotContains(self.client.get(response["Location"]), "Email delivery is temporarily unavailable")
        self.assertEqual(application.photos.count(), 2)
        self.assertEqual(application.notification_email.status, ApplicationEmail.Status.FAILED)
        staff = get_user_model().objects.create_superuser("reviewer", "reviewer@example.com", "password")
        self.client.force_login(staff)
        with override_settings(RESEND_API_KEY="test-key"):
            result = self.client.post(reverse("admin:camp_application_changelist"), {
                "action": "retry_application_emails", "_selected_action": [application.pk],
            })
        self.assertEqual(result.status_code, 302)
        application.notification_email.refresh_from_db()
        self.assertEqual(application.notification_email.status, ApplicationEmail.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)

    def test_model_sizes_follow_gender_and_are_required(self):
        response = self.client.post(reverse("join"), self.submission_data(
            shoe_size="6", pants_size="32", dress_size="", skirt_size="", top_size="M",
        ))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertFormError(response.context["form"], "skirt_size", "This field is required.")
        self.assertContains(response, 'href="#error-dress_size"')
        self.assertContains(response, "Dress size: This field is required.")
        self.assertContains(response, "For security, photographs are not retained")
        response = self.client.post(reverse("join"), self.submission_data(
            gender="male", shoe_size="9", pants_size="32", top_size="M",
            dress_size="10", skirt_size="10",
        ))
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get()
        self.assertEqual(application.dress_size, "")
        self.assertEqual(application.skirt_size, "")
        self.assertNotContains(self.client.get(reverse("camp:shared_application", args=[application.share_token])), "Dress size")

    def test_submission_saves_application_and_required_photos(self):
        response = self.client.post(
            reverse("join"),
            self.submission_data(),
        )
        application = Application.objects.get()
        self.assertEqual(response.status_code, 302)
        whatsapp_redirect = urlsplit(response["Location"])
        self.assertEqual(whatsapp_redirect.scheme, "https")
        self.assertEqual(whatsapp_redirect.netloc, "wa.me")
        self.assertEqual(whatsapp_redirect.path, "/27681946795")
        message = parse_qs(whatsapp_redirect.query)["text"][0]
        self.assertIn(application.application_number, message)
        self.assertIn("Applicant: Jordan Example", message)
        self.assertIn("jordan@example.com", message)
        self.assertIn("PHOTOS: http://testserver/training/application/", message)
        self.assertIn("FULL APPLICATION: http://testserver/training/application/", message)
        self.assertTrue(application.application_number.startswith("LFA-2026-"))
        self.assertEqual(application.age, 20)
        self.assertIsNone(application.date_of_birth)
        self.assertEqual(application.city, "Cape Town")
        self.assertEqual(application.town, "Sea Point")
        self.assertEqual(application.age_category, "")
        self.assertEqual(application.gender, Application.Gender.FEMALE)
        self.assertNotIn("Date of Birth:", message)
        self.assertEqual(application.preferred_days, [])
        self.assertEqual(application.areas_of_interest, [])
        self.assertIsNone(application.available_full_five_weeks)
        self.assertTrue(application.has_modelling_experience)
        self.assertEqual(application.tiktok_handle, "@jordanstudio")
        self.assertEqual(application.photos.count(), 2)
        self.assertSetEqual(
            set(application.photos.values_list("photo_type", flat=True)),
            {
                ApplicationPhoto.PhotoType.HEADSHOT,
                ApplicationPhoto.PhotoType.FULL_LENGTH,
            },
        )
        self.assertTrue(
            all(Path(photo.image.path).is_file() for photo in application.photos.all())
        )

    def test_submission_accepts_photo_larger_than_previous_limit(self):
        oversized_photo = make_png() + b"x" * (8 * 1024 * 1024 + 1)
        response = self.client.post(
            reverse("join"),
            self.submission_data(
                headshot=SimpleUploadedFile(
                    "large-headshot.png",
                    oversized_photo,
                    content_type="image/png",
                )
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ApplicationPhoto.objects.count(), 2)
        self.assertGreater(
            ApplicationPhoto.objects.get(photo_type="headshot").image.size,
            8 * 1024 * 1024,
        )

    def test_success_page_offers_a_prepared_whatsapp_message_after_saving(self):
        self.client.post(
            reverse("join"),
            self.submission_data(about="A long personal statement not sent to WhatsApp."),
        )
        application = Application.objects.get()
        response = self.client.get(
            reverse("camp:success", kwargs={"token": application.share_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application received")
        self.assertContains(response, "tap Send")
        self.assertContains(response, "Send application via WhatsApp")
        self.assertContains(response, application.application_number)
        self.assertNotContains(response, "sent automatically")
        self.assertTrue(response.context["whatsapp_url"].startswith("https://wa.me/"))
        message = parse_qs(
            urlsplit(response.context["whatsapp_url"]).query
        )["text"][0]
        for expected in (
            application.application_number,
            "Jordan Example",
            "20",
            "Gender: Female",
            "City: Cape Town",
            "Town: Sea Point",
            "jordan@example.com",
            "Student",
            "Modelling experience: Yes",
            "Community theatre",
            "Instagram: @jordan",
            "TikTok: @jordanstudio",
            "PHOTOS: http://testserver/training/application/",
            "FULL APPLICATION: http://testserver/training/application/",
        ):
            self.assertIn(expected, message)
        self.assertNotIn("A long personal statement", message)
        self.assertNotIn("Preferred Days:", message)
        self.assertNotIn("Interested In:", message)
        self.assertNotIn("Preferred Time:", message)
        self.assertNotIn("graph.facebook.com", response.context["whatsapp_url"])
        full_application = self.client.get(
            reverse(
                "camp:shared_application",
                args=[application_share_token(application)],
            )
        )
        self.assertEqual(full_application.status_code, 200)
        self.assertContains(full_application, "Jordan Example")
        self.assertContains(full_application, "Community theatre")
        self.assertNotIn("Age category:", message)
        self.assertNotIn("Available day:", message)
        self.assertNotIn("Available for Full 6 Weeks:", message)
        self.assertContains(full_application, "Female")
        self.assertContains(full_application, "Cape Town")
        self.assertContains(full_application, "Sea Point")
        self.assertNotContains(full_application, "Date of birth")
        self.assertContains(full_application, "Modelling experience")

    def test_two_required_photos_are_saved_and_visible_on_private_photo_page(self):
        self.client.post(reverse("join"), self.submission_data())
        application = Application.objects.get()
        self.assertEqual(application.photos.count(), 2)
        photos_response = self.client.get(
            reverse("camp:shared_photos", args=[application.share_token])
        )
        self.assertEqual(photos_response.status_code, 200)
        self.assertContains(photos_response, "Profile / selfie")
        self.assertContains(photos_response, "Full-length")
        self.assertNotContains(photos_response, "Additional")

    def test_idempotency_key_prevents_duplicate_applications(self):
        data = self.submission_data()
        first_response = self.client.post(reverse("join"), data)
        duplicate_response = self.client.post(
            reverse("join"),
            self.submission_data(submission_key=data["submission_key"]),
        )
        self.assertEqual(urlsplit(first_response["Location"]).netloc, "wa.me")
        self.assertEqual(urlsplit(duplicate_response["Location"]).netloc, "wa.me")
        self.assertEqual(
            urlsplit(duplicate_response["Location"]).path,
            "/27681946795",
        )
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(ApplicationPhoto.objects.count(), 2)

    def test_missing_age_or_required_photo_is_rejected(self):
        no_age = self.submission_data()
        no_age.pop("age")
        response = self.client.post(reverse("join"), no_age)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

        no_headshot = self.submission_data()
        no_headshot.pop("headshot")
        response = self.client.post(reverse("join"), no_headshot)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_city_and_town_are_required_separately(self):
        for field in ("city", "town"):
            with self.subTest(field=field):
                data = self.submission_data()
                data.pop(field)
                response = self.client.post(reverse("join"), data)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Application.objects.exists())

    def test_modelling_experience_is_required(self):
        no_available_days = self.submission_data()
        no_available_days.pop("preferred_days")
        response = self.client.post(reverse("join"), no_available_days)
        self.assertEqual(response.status_code, 302)
        Application.objects.all().delete()

        no_experience_answer = self.submission_data()
        no_experience_answer.pop("has_modelling_experience")
        response = self.client.post(reverse("join"), no_experience_answer)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

        no_gender_answer = self.submission_data()
        no_gender_answer.pop("gender")
        response = self.client.post(reverse("join"), no_gender_answer)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_no_modelling_experience_discards_optional_experience_details(self):
        self.client.post(
            reverse("join"),
            self.submission_data(
                has_modelling_experience="no",
                previous_experience="Should not be stored",
            ),
        )
        application = Application.objects.get()
        self.assertFalse(application.has_modelling_experience)
        self.assertEqual(application.previous_experience, "")

    def test_training_age_category_must_match_typed_age(self):
        from .forms import TrainingApplicationForm
        form = TrainingApplicationForm(self.submission_data(age_category="kids"))
        self.assertFalse(form.is_valid())
        self.assertIn("does not match the selected category", form.errors["age_category"][0])

    def test_phone_and_email_formats_are_validated(self):
        from .forms import TrainingApplicationForm
        for field, value in (("phone", "12345"), ("whatsapp_number", "06819467a5"), ("phone", "+27681946795"), ("email", "name@domain")):
            with self.subTest(field=field, value=value):
                form = TrainingApplicationForm(self.submission_data(**{field: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_kids_category_accepts_age_12_and_shows_2027_notice(self):
        response = self.client.post(
            reverse("join"),
            self.submission_data(
                age="12",
                age_category="kids",
                gender="male",
                guardian_name="Jordan Guardian",
                guardian_phone="0123456789",
                guardian_consent="on",
            ),
        )
        application = Application.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(application.age, 12)
        self.assertEqual(application.age_category, "")
        self.assertEqual(application.gender, Application.Gender.MALE)

    def test_age_outside_category_ranges_is_rejected(self):
        for age in ("4", "29"):
            with self.subTest(age=age):
                response = self.client.post(
                    reverse("join"),
                    self.submission_data(age=age),
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Application.objects.exists())
                self.assertContains(
                    response,
                    "Applicants must be between 5 and 28 years old.",
                )

    def test_under_18_applicant_needs_guardian_details_and_consent(self):
        response = self.client.post(
            reverse("join"),
            self.submission_data(
                age="16",
                age_category="teens",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())
        self.assertContains(response, "parent or guardian")

    @patch("camp.views.ModelApplicationForm.save", side_effect=OSError("Disk unavailable"))
    def test_storage_failure_shows_error_and_does_not_redirect_to_whatsapp(self, _save):
        response = self.client.post(
            reverse("join"),
            self.submission_data(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "because of a technical problem",
        )
        self.assertFalse(Application.objects.exists())

    def test_invalid_share_tokens_do_not_reveal_applications_or_photos(self):
        self.assertEqual(
            self.client.get("/application/00000000-0000-0000-0000-000000000000/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                "/application/00000000-0000-0000-0000-000000000000/photos/"
            ).status_code,
            404,
        )


class WhatsAppHandoffTests(TestCase):
    def test_message_url_uses_configured_international_number_and_encoded_links(self):
        application = Application.objects.create(
            full_name="Morgan Applicant",
            email="morgan@example.com",
            phone="0123456789",
            whatsapp_number="0671234567",
            age=21,
            age_category=Application.AgeCategory.SENIORS,
            gender=Application.Gender.FEMALE,
            city="Durban",
            town="Umhlanga",
            current_occupation="Student",
            preferred_days=["Friday"],
            available_full_five_weeks=True,
            has_modelling_experience=True,
            previous_experience="No previous modelling experience",
            social_handle="@morgan",
        )
        request = RequestFactory().get("/", HTTP_HOST="agency.example", secure=True)
        with override_settings(
            LOCAL_FACES_WHATSAPP_NUMBER="27681946795",
            ALLOWED_HOSTS=["agency.example"],
        ):
            url = build_application_whatsapp_url(application, request)
        parts = urlsplit(url)
        message = parse_qs(parts.query)["text"][0]
        self.assertEqual(parts.netloc, "wa.me")
        self.assertEqual(parts.path, "/27681946795")
        self.assertIn("https://agency.example/training/application/", message)
        self.assertIn("/photos/", message)
        self.assertIn("Morgan Applicant", message)
        self.assertIn("morgan@example.com", message)
        self.assertIn("Available day: Friday", message)
        self.assertIn("Available for Full 6 Weeks: Yes", message)
        self.assertIn("Age category: Seniors (19–28)", message)
        self.assertIn("Gender: Female", message)
        self.assertIn("Modelling experience: Yes", message)
        self.assertIn("Instagram: @morgan", message)
        self.assertIn("TikTok: Not provided", message)
        self.assertNotIn("Preferred Days:", message)
        self.assertNotIn("Interested In:", message)
        self.assertNotIn("Preferred Time:", message)
        self.assertIn("PHOTOS:", message)
        self.assertIn("FULL APPLICATION:", message)
        self.assertNotIn("graph.facebook.com", url)

    @override_settings(
        LOCAL_FACES_WHATSAPP_NUMBER="+27 67 101 2841",
        ALLOWED_HOSTS=["agency.example"],
    )
    def test_invalid_whatsapp_number_configuration_fails_explicitly(self):
        application = Application.objects.create(
            full_name="Morgan Applicant",
            email="morgan@example.com",
            phone="0123456789",
            city="Durban",
        )
        request = RequestFactory().get("/", HTTP_HOST="agency.example", secure=True)
        from django.core.exceptions import ImproperlyConfigured

        with self.assertRaises(ImproperlyConfigured):
            build_application_whatsapp_url(application, request)


class PrivatePhotoTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=Path(self.media_directory.name)
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def test_photo_file_is_private_and_accessible_only_via_random_token(self):
        application = Application.objects.create(
            full_name="Taylor Example",
            email="taylor@example.com",
            phone="0123456789",
            city="Johannesburg",
            privacy_consent=True,
            photo_consent=True,
        )
        photo = ApplicationPhoto.objects.create(
            application=application,
            image=SimpleUploadedFile(
                "portrait.png", make_png(), content_type="image/png"
            ),
            original_name="portrait.png",
        )
        token = application_share_token(application)
        response = self.client.get(
            reverse("camp:shared_photo", args=[token, photo.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertTrue(response.streaming)
        response.close()
        self.assertEqual(
            self.client.get(f"/private/{photo.image.name}").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("camp:shared_application", args=[uuid4()])
            ).status_code,
            404,
        )
