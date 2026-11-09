from html.parser import HTMLParser
from decimal import Decimal
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from camp.models import Application
from camp.tests import make_png
from .models import TrainingOrder
from .payfast import signature

class PageLinksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.fragment_links = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a":
            href = attributes.get("href", "")
            if href.startswith("#"):
                self.fragment_links.add(href[1:])


class HomePageTests(TestCase):
    def test_homepage_renders_editorial_sections(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL PEOPLE.")
        self.assertContains(response, "LOCAL FACES")
        self.assertContains(response, "MODELLING ACADEMY")
        self.assertContains(response, "Turn Your Look Into an Opportunity. Turn Your Name Into a Brand.")
        self.assertContains(response, "More Than Modelling. We’re Building Brands.")
        self.assertContains(response, "Your Look. Your Brand. Your Future.")
        self.assertContains(response, "What You’ll Walk Away With")
        self.assertContains(response, "Walk away focused, confident and career-ready")
        self.assertContains(response, "agency/img/walkaway1.jpg")
        self.assertNotContains(response, 'class="walkaway"')
        self.assertNotContains(response, "SUMMER MODELLING ACADEMY")
        self.assertContains(response, "Get Represented")
        self.assertContains(response, "agency/img/founder.jpeg")
        self.assertContains(response, "agency/img/founder1.jpeg")
        self.assertContains(response, "agency/img/hero-collage.jpg")
        for label in ("Home", "About", "Talent", "Training", "Contact"):
            self.assertContains(response, f">{label}</a>")

    def test_model_slideshow_has_requested_images(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "agency/img/model.jpeg", count=1)
        self.assertNotContains(response, "agency/img/model1.jpeg")
        self.assertContains(response, f'href="{reverse("models_gallery")}"')
        gallery = self.client.get(reverse("models_gallery"))
        self.assertContains(gallery, "soon to be uploaded")
        self.assertNotContains(gallery, "agency/img/model")

    def test_founder_portfolio_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("founder_portfolio")}"')
        portfolio = self.client.get(reverse("founder_portfolio"))
        for filename in ("brand.jpeg", "brand1.jpeg", "brand2.jpeg", "brand4.jpeg", "brand5.jpeg", "brand6.jpeg"):
            self.assertContains(portfolio, f"agency/img/{filename}")
        self.assertNotContains(portfolio, "brand3.jpeg")

    def test_content_creator_slideshow_has_requested_images(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("entertainers_gallery")}"')
        self.assertContains(response, "agency/img/1000834848.jpg", count=1)
        self.assertNotContains(response, "agency/img/e1.jpeg")
        gallery = self.client.get(reverse("entertainers_gallery"))
        self.assertContains(gallery, "soon to be uploaded")
        self.assertNotContains(gallery, "agency/img/model")

    def test_selfie_example_in_model_and_training_forms(self):
        self.assertContains(self.client.get(reverse("join")), "agency/img/self.jpeg")
        response = self.client.post(reverse("training_shop"), {"training": "course", "city": "Durban"})
        self.assertRedirects(response, reverse("training_application"))
        self.assertContains(self.client.get(reverse("training_application")), "agency/img/self.jpeg")
        response = self.client.post(reverse("training_shop"), {"training": "individual", "city": "Durban", "hours": "1"})
        self.assertRedirects(response, reverse("training_application"))
        self.assertContains(self.client.get(reverse("training_application")), "agency/img/self.jpeg")

    def test_logos_use_talent_agency_branding(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<span class="brand-tagline">Talent Agency</span>', count=3)
        self.assertContains(response, 'aria-label="Local Faces Talent Agency home"', count=2)
        self.assertContains(response, 'aria-label="Local Faces Talent Agency"')
        self.assertNotContains(response, '<span class="brand-tagline">Entertainment')
        self.assertContains(response, "Models of all ages and sizes &amp; Content Creators")
        self.assertContains(response, "Training and Packages Available")
        self.assertContains(response, "Production, Podcast &amp; Content Creation")
        self.assertNotContains(response, "Actors")
        self.assertNotContains(response, "MCs")

    def test_navigation_has_accessible_mobile_menu(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'aria-expanded="false" aria-controls="primary-navigation" data-menu-toggle')
        self.assertContains(response, 'id="primary-navigation" aria-label="Main navigation" data-navigation')
        for label in ("Home", "About", "Talent", "Training", "Cart", "Contact"):
            self.assertContains(response, f">{label}</a>")
        for fragment in ("photography", "entertainment", "merchandise"):
            self.assertNotContains(response, f'href="{reverse("home")}#{fragment}"')
            self.assertContains(response, f'id="{fragment}"')

    def test_homepage_navigation_and_fragment_links_resolve(self):
        response = self.client.get("/")
        parser = PageLinksParser()
        parser.feed(response.content.decode())

        self.assertEqual(parser.fragment_links - parser.ids, set())

    def test_talent_pool_links_open_category_form(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("join")}"', count=3)
        self.assertContains(response, "<span>Models</span><span>Talent</span><span>Training</span>")
        self.assertContains(response, "A home for Models and Talent of all ages, sizes and backgrounds.")

        response = self.client.get(reverse("join"))
        self.assertContains(response, 'name="category" value="model"')
        self.assertContains(response, 'name="category" value="talent"')
        self.assertContains(response, "MODEL APPLICATION")
        self.assertContains(response, 'name="shoe_size"')
        self.assertContains(response, 'name="dress_size"')
        self.assertContains(response, "Talent applications are coming soon.")

    def test_training_details_are_visible_on_home_and_application(self):
        for url in (reverse("home"), reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "December intake fully booked!", count=3)
                self.assertContains(response, "Registrations for 2026 are officially closed.", count=3)
                self.assertContains(response, "December 2026 Academy Fashion Show &amp; Graduation")
                self.assertContains(response, "R50 per person")
                self.assertContains(response, "Shared upon enquiry")
                self.assertContains(response, 'href="mailto:info@localfaces.co.za"')
                self.assertContains(response, 'href="https://wa.me/27681946795"')
                self.assertContains(response, "2027 registrations now open!")
                self.assertContains(response, "Join Local Faces Modelling Academy in Johannesburg, Durban or Cape Town, hosted by Semu.")
                self.assertContains(response, "Limited spaces! First come, first serve. Registration closes once all spaces are filled.")
                self.assertContains(response, "Secure your spot today!")
                self.assertNotContains(response, "Training is available for 2027, terms 1 to 4.")
                self.assertContains(response, "What You’ll Walk Away With", count=1)
                self.assertContains(response, "Walk away focused, confident and career-ready", count=1)
                self.assertContains(response, "agency/img/walkaway1.jpg", count=1)
                self.assertContains(response, "6-week intensive")
                self.assertContains(response, "Durban")
                self.assertContains(response, "Johannesburg")
                self.assertContains(response, "Cape Town")
                self.assertContains(response, "Hosted by Semu", count=3)
                self.assertContains(response, "Registration: R500")
                self.assertContains(response, "non-refundable")
                self.assertContains(response, "Course: R2,500")

    def test_city_details_and_purchase_links_on_training_pages(self):
        for url in (reverse("home"), reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            response = self.client.get(url)
            html = response.content.decode()
            self.assertContains(response, "click a city below to view fees and book training.")
            self.assertContains(response, "View fees and booking", count=3)
            self.assertContains(response, '<details class="training-city">', count=3)
            for city in ("Durban", "Johannesburg", "Cape Town"):
                with self.subTest(url=url, city=city):
                    start = html.index(f'<summary><strong>{city}</strong>')
                    panel = html[start:html.index("</details>", start)]
                    self.assertIn("December intake fully booked!", panel)
                    self.assertIn("Registrations for 2026 are officially closed. We look forward to welcoming new talent in 2027!", panel)
                    self.assertIn("Registration: R500", panel)
                    self.assertIn("(non-refundable)", panel)
                    self.assertIn("Course: R2,500", panel)
                    self.assertIn("Total: R3,000", panel)
                    self.assertIn("remaining R2,500 in one payment or in two monthly payments of R1,250", panel)
                    self.assertIn("R1,500 per hour", panel)
                    self.assertIn('href="mailto:info@localfaces.co.za"', panel)
                    self.assertIn(
                        f'href="{reverse("training_shop")}?city={quote(city)}#training-selection"',
                        panel,
                    )

    def test_training_links_go_to_details_and_shop(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<a class="service" href="#training-registration">')
        self.assertContains(response, '<div class="training-registration" id="training-registration">')
        self.assertContains(response, '<p class="training-fees"><strong>Registration: R500</strong>', count=3)
        self.assertContains(response, '<div class="academy-details" id="training-information">')
        self.assertContains(response, f'href="{reverse("training_shop")}"')
        self.assertContains(
            response,
            f'href="{reverse("camp:apply")}">Explore training</a>',
        )
        self.assertNotContains(response, "Apply for 2027 training")
        html = response.content.decode()
        self.assertLess(html.index("Learn. Practise. Grow."), html.index("LOCAL FACES<br>"))
        self.assertLess(html.index("Turn Your Look Into an Opportunity. Turn Your Name Into a Brand."), html.index("<h3>Training details</h3>"))
        self.assertLess(html.index("<h3>Training details</h3>"), html.index("December intake fully booked!"))
        self.assertLess(html.index("December intake fully booked!"), html.index("R1,500 per hour"))
        self.assertLess(html.index("R1,500 per hour"), html.index("agency/img/walkaway1.jpg"))
        self.assertLess(html.index("agency/img/walkaway1.jpg"), html.index("What You’ll Walk Away With"))

    def test_course_topics_appear_on_homepage_and_course_details(self):
        topics = (
            "Runway &amp; Modelling:",
            "Understanding the Industry:",
            "Confidence &amp; Career Longevity:",
            "Personal Branding &amp; Social Media:",
            "Industry Knowledge &amp; Representation",
            "Monetising Your Talent:",
        )
        home = self.client.get(reverse("home"))
        self.assertContains(home, "What the training covers")
        for topic in topics:
            self.assertContains(home, topic, count=1)
        for url in (reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            response = self.client.get(url)
            self.assertContains(response, "What the training covers")
            for topic in topics:
                self.assertContains(response, topic)

    def test_academy_opportunity_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("academy_opportunity"))
        self.assertContains(response, f'href="{reverse("academy_opportunity")}">Start your academy →</a>')
        response = self.client.get(reverse("academy_opportunity"))
        self.assertContains(response, "agency/img/model4.jpeg")
        self.assertNotContains(response, "agency/img/academy-main.jpg")
        self.assertContains(response, "Contact the academy to enquire")
        self.assertContains(response, 'href="mailto:info@localfaces.co.za?subject=Academy%20opportunity%20enquiry"')
        for text in ("investment", "payment", "instalment", "R5,000", "R1,666", 'name="city"'):
            self.assertNotContains(response, text)


@override_settings(
    PAYFAST_MERCHANT_ID="10000100",
    PAYFAST_MERCHANT_KEY="test-key",
    PAYFAST_PASSPHRASE="test passphrase",
    PAYFAST_SITE_URL="https://example.com",
    PAYFAST_SANDBOX=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RESEND_API_KEY="test-key",
    DEFAULT_FROM_EMAIL="sender@example.com",
)
class TrainingShopTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        settings_override = override_settings(MEDIA_ROOT=Path(self.media_directory.name))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def application_data(self, **overrides):
        pending = self.client.session["pending_training"]
        data = {
            "submission_key": pending["submission_key"],
            "full_name": "Alex Example", "email": "alex@example.com",
            "phone": "0123456789", "whatsapp_number": "0123456789",
            "age": "20", "age_category": "seniors", "gender": "female",
            "city": pending["city"], "town": "Central", "current_occupation": "Student",
            "preferred_days": "Friday", "available_full_five_weeks": "yes",
            "has_modelling_experience": "no", "shoe_size": "6", "pants_size": "32",
            "dress_size": "10", "skirt_size": "10", "top_size": "M",
            "privacy_consent": "on", "photo_consent": "on",
            "headshot": SimpleUploadedFile("headshot.png", make_png(), content_type="image/png"),
            "full_length_photo": SimpleUploadedFile("full.png", make_png(), content_type="image/png"),
        }
        data.update(overrides)
        return data

    def add_item(self, **overrides):
        data = {"training": "course", "city": "Durban", "hours": "1"}
        data.update(overrides)
        response = self.client.post(reverse("training_shop"), data)
        if response.status_code == 302 and response["Location"] == reverse("training_application"):
            return self.client.post(reverse("training_application"), self.application_data())
        return response

    def create_order(self):
        return TrainingOrder.objects.create(total=Decimal("3500.00"), items=[])

    def test_existing_academy_item_in_mixed_cart(self):
        session = self.client.session
        session["training_cart"] = [{"training": "academy", "city": "Pretoria"}]
        session.save()
        self.add_item()
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual(cart.context["total"], Decimal("2166.67"))
        self.assertContains(cart, "Proposed city: Pretoria")
        self.assertContains(cart, "R1,666.67 in month two and R1,666.66 in month three")
        self.assertNotContains(cart, "Term  · Pretoria")
        self.assertEqual(cart.context["items"][0]["remaining_installments"], ["1666.67", "1666.66"])
        self.assertEqual(cart.context["items"][1]["application_number"], Application.objects.get().application_number)
        self.assertContains(cart, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_group_application_is_required_and_records_sizes_and_photos(self):
        response = self.client.post(reverse("training_shop"), {
            "training": "course", "city": "Durban", "hours": "1",
        })
        self.assertRedirects(response, reverse("training_application"))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.assertRedirects(self.client.post(reverse("training_checkout")), reverse("training_cart"))
        page = self.client.get(reverse("training_application"))
        self.assertContains(page, 'name="shoe_size"')
        self.assertContains(page, 'name="dress_size"')
        data = self.application_data(dress_size="", skirt_size="")
        data.pop("headshot")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "headshot", "This field is required.")
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertContains(response, 'href="#error-headshot"')
        self.assertContains(response, 'href="#error-dress_size"')
        self.assertContains(response, "For security, photographs are not retained")
        self.assertFalse(Application.objects.exists())
        response = self.client.post(reverse("training_application"), self.application_data())
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        application = Application.objects.get()
        self.assertEqual(application.kind, Application.Kind.TRAINING)
        self.assertEqual((application.shoe_size, application.dress_size, application.top_size), ("6", "10", "M"))
        self.assertEqual(application.photos.count(), 2)
        self.assertContains(self.client.get(reverse("camp:shared_application", args=[application.share_token])), "Dress size")
        self.assertEqual(self.client.session["training_cart"][0]["application_number"], application.application_number)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["info@localfaces.com"])
        self.assertIn("Training: Group course", email.body)
        self.assertIn("Training city: Durban", email.body)
        self.assertIn("Full name: Alex Example", email.body)
        self.assertIn(reverse("admin:camp_application_change", args=[application.pk]), email.body)
        self.assertEqual(email.attachments, [])
        self.assertEqual(application.notification_email.status, "sent")

    def test_application_page_shows_bank_details_and_no_payment_choice(self):
        self.client.post(reverse("training_shop"), {"training": "course", "city": "Durban"})
        page = self.client.get(reverse("training_application"))
        self.assertContains(page, "1330686349")
        self.assertNotContains(page, "balance_payment_plan")

    def test_cart_links_stored_application_to_whatsapp(self):
        self.add_item()
        application = Application.objects.get()
        cart = self.client.get(reverse("training_cart"))
        self.assertContains(cart, "https://wa.me/27681946795?")
        self.assertContains(cart, "Send application on WhatsApp")
        self.assertContains(cart, application.application_number.replace(" ", "+")[:5])

    @override_settings(RESEND_API_KEY="")
    def test_training_email_failure_preserves_application_and_cart(self):
        response = self.add_item()
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        application = Application.objects.get()
        self.assertEqual(application.notification_email.status, "failed")
        self.assertEqual(application.photos.count(), 2)
        cart = self.client.get(reverse("training_cart"))
        self.assertNotContains(cart, "Email delivery is temporarily unavailable")
        self.assertContains(cart, application.application_number)
        self.assertEqual(len(cart.context["items"]), 1)

    @override_settings(EMAIL_BACKEND="camp.email_backend.ResendEmailBackend")
    @patch("camp.email_backend.urlopen", side_effect=OSError("service unavailable"))
    def test_resend_failure_keeps_training_application_for_retry(self, _urlopen):
        response = self.add_item()
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        application = Application.objects.get()
        self.assertEqual(application.notification_email.status, "failed")
        self.assertEqual(application.photos.count(), 2)
        self.assertNotContains(self.client.get(reverse("training_cart")), "Email delivery is temporarily unavailable")

    def test_group_application_prefills_city_and_preserves_edited_city(self):
        for city in ("Durban", "Johannesburg", "Cape Town"):
            with self.subTest(city=city):
                self.client.post(reverse("training_shop"), {
                    "training": "course", "city": city,
                })
                response = self.client.get(reverse("training_application"))
                self.assertEqual(response.context["form"]["city"].value(), city)
                self.assertContains(response, f'value="{city}"')

        data = self.application_data(city="Pretoria", dress_size="")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertEqual(response.context["form"]["city"].value(), "Pretoria")
        response = self.client.post(reverse("training_application"), self.application_data(city="Pretoria"))
        self.assertRedirects(response, reverse("training_cart"))
        self.assertEqual(Application.objects.get().city, "Pretoria")
        self.assertEqual(self.client.session["training_cart"][0]["city"], "Cape Town")

    def test_legacy_group_item_cannot_bypass_application(self):
        session = self.client.session
        session["training_cart"] = [{"training": "course", "city": "Durban", "hours": 1}]
        session.save()
        response = self.client.get(reverse("training_cart"))
        self.assertContains(response, "needs an application")
        self.assertNotContains(response, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_one_on_one_requires_talent_style_form_before_checkout(self):
        response = self.client.post(reverse("training_shop"), {
            "training": "individual", "city": "Johannesburg", "hours": "2",
        })
        self.assertRedirects(response, reverse("training_application"))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        page = self.client.get(reverse("training_application"))
        self.assertContains(page, "One-on-one training")
        self.assertNotContains(page, "R500 registration")
        self.assertNotContains(page, 'name="age_category"')
        self.assertNotContains(page, 'name="preferred_days"')
        self.assertNotContains(page, 'name="available_full_five_weeks"')
        self.assertContains(page, 'name="shoe_size"')
        self.assertContains(page, 'name="headshot"')
        self.assertEqual(page.context["form"]["city"].value(), "Johannesburg")

        data = self.application_data(dress_size="", skirt_size="")
        data.pop("headshot")
        data.pop("age_category")
        data.pop("preferred_days")
        data.pop("available_full_five_weeks")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "headshot", "This field is required.")
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertFalse(Application.objects.exists())

        data = self.application_data()
        for field in ("age_category", "preferred_days", "available_full_five_weeks"):
            data.pop(field)
        self.assertRedirects(self.client.post(reverse("training_application"), data), reverse("training_cart"))
        application = Application.objects.get()
        self.assertEqual(application.kind, Application.Kind.TRAINING)
        self.assertEqual((application.city, application.dress_size, application.photos.count()), ("Johannesburg", "10", 2))
        cart = self.client.get(reverse("training_cart"))
        self.assertContains(cart, application.application_number)
        self.assertEqual(cart.context["total"], Decimal("3000.00"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Training: One-on-one", mail.outbox[0].body)
        self.assertIn("Hours: 2", mail.outbox[0].body)
        self.assertIn("Training city: Johannesburg", mail.outbox[0].body)
        self.assertContains(cart, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_legacy_one_on_one_item_cannot_bypass_application(self):
        session = self.client.session
        session["training_cart"] = [{"training": "individual", "city": "Durban", "hours": 1}]
        session.save()
        response = self.client.get(reverse("training_cart"))
        self.assertContains(response, "needs an application")
        self.assertNotContains(response, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_group_application_male_and_selection_cannot_be_bypassed(self):
        self.assertRedirects(self.client.get(reverse("training_application")), reverse("training_shop"))
        self.client.post(reverse("training_shop"), {"training": "course", "city": "Durban"})
        response = self.client.post(reverse("training_application"), self.application_data(
            gender="male", dress_size="10", skirt_size="10",
        ))
        self.assertRedirects(response, reverse("training_cart"))
        applicant = Application.objects.get()
        self.assertEqual((applicant.dress_size, applicant.skirt_size), ("", ""))
        applicant.delete()
        response = self.client.get(reverse("training_cart"))
        self.assertContains(response, "needs an application")
        self.assertNotContains(response, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    @patch("agency.shop.TrainingApplicationForm.save", side_effect=OSError("Disk unavailable"))
    def test_group_application_storage_failure_does_not_add_to_cart(self, _save):
        self.client.post(reverse("training_shop"), {"training": "course", "city": "Durban"})
        response = self.client.post(reverse("training_application"), self.application_data())
        self.assertContains(response, "because of a technical problem")
        self.assertEqual(self.client.session.get("training_cart", []), [])
        self.assertFalse(Application.objects.exists())

    def test_academy_does_not_accept_new_cart_items(self):
        response = self.client.post(reverse("academy_opportunity"), {"city": "Pretoria"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.session.get("training_cart", []), [])

    def test_cart_totals_and_eft_details(self):
        self.assertEqual(self.add_item().status_code, 302)
        self.assertEqual(self.add_item(training="individual", city="Johannesburg", hours="2").status_code, 302)
        response = self.client.get(reverse("training_cart"))
        self.assertEqual(response.context["total"], Decimal("3500.00"))
        self.assertContains(response, "remaining R2500.00")
        self.assertContains(response, "proof of payment")
        for value in ("Nedbank", "localfaces Entertainment", "1330686349", "Applicant's name", "info@localfaces.co.za"):
            self.assertContains(response, value)
        self.assertNotContains(response, "For an academy opportunity without an applicant")
        self.assertNotContains(response, "training type, term and city for each booking")
        self.assertNotContains(response, "For an academy opportunity, include")
        self.assertContains(response, "Pay by EFT")
        self.assertNotContains(response, "PayFast")
        self.assertNotContains(response, reverse("training_checkout"))
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_invalid_selection_and_remove(self):
        self.assertEqual(self.add_item(city="Pretoria").status_code, 200)
        for training in ("course", "individual"):
            for city in ("Pretoria", "other"):
                with self.subTest(training=training, city=city):
                    response = self.add_item(training=training, city=city, other_city="Pretoria")
                    self.assertFormError(response.context["form"], "city", "Select a valid choice. %(value)s is not one of the available choices." % {"value": city})
        self.assertEqual(self.add_item(training="individual", hours="0").status_code, 200)
        self.assertEqual(self.add_item(city="Nowhere").status_code, 200)
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.add_item()
        self.client.post(reverse("training_cart_remove", args=[0]))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.assertEqual(self.client.post(reverse("training_cart_remove", args=[0])).status_code, 400)

    def test_select_city_and_add_group_course(self):
        response = self.client.get(reverse("training_shop"))
        self.assertContains(response, "Make your selection")
        self.assertContains(response, 'href="#training-information"')
        self.assertContains(response, 'id="training-information"')
        self.assertContains(response, 'data-training-details="course"')
        self.assertContains(response, 'data-training-shop')
        self.assertContains(response, 'Group course - R500 non-refundable registration')
        self.assertContains(response, 'Group course: R500 non-refundable registration.')
        self.assertContains(response, '<select name="city"')
        self.assertNotContains(response, '>Other city</option>')
        for city in ("Durban", "Johannesburg", "Cape Town"):
            self.assertContains(response, f'value="{city}"')
            added = self.add_item(city=city, hours="")
            self.assertRedirects(added, reverse("training_cart"))
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual(cart.context["total"], Decimal("1500.00"))
        self.assertEqual([item["city"] for item in cart.context["items"]], ["Durban", "Johannesburg", "Cape Town"])

    def test_city_purchase_links_preselect_city_without_changing_posted_selection(self):
        for city in ("Durban", "Johannesburg", "Cape Town"):
            with self.subTest(city=city):
                response = self.client.get(reverse("training_shop"), {"city": city})
                self.assertEqual(response.context["form"]["city"].value(), city)
                self.assertContains(response, f'<option value="{city}" selected>')
        response = self.client.post(
            reverse("training_shop") + "?city=Durban",
            {"training": "course", "city": "Cape Town"},
        )
        self.assertRedirects(response, reverse("training_application"))
        self.assertEqual(self.client.session["pending_training"]["city"], "Cape Town")

    def test_outdated_other_city_selection_requires_reselection(self):
        session = self.client.session
        session["pending_training"] = {"training": "individual", "city": "Pretoria", "hours": 1}
        session.save()
        response = self.client.get(reverse("training_application"), follow=True)
        self.assertRedirects(response, reverse("training_shop"))
        self.assertContains(response, "Training is now available only in Durban, Johannesburg and Cape Town.")
        self.assertEqual(self.client.session.get("training_cart", []), [])

    def test_one_on_one_allows_three_cities(self):
        for city in ("Durban", "Johannesburg", "Cape Town"):
            with self.subTest(city=city):
                self.assertRedirects(self.add_item(training="individual", city=city, hours="1"), reverse("training_cart"))
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual([item["city"] for item in cart.context["items"]], ["Durban", "Johannesburg", "Cape Town"])

    def test_registration_fee_is_r500_and_discloses_balance(self):
        self.add_item(hours="")
        checkout = self.client.get(reverse("training_cart"))
        self.assertContains(checkout, "Total payable now: R500.00")
        self.assertContains(checkout, "remaining R2500.00")
        self.assertContains(checkout, "info@localfaces.co.za")
        self.assertContains(checkout, "Applicant's name")
        self.assertContains(checkout, "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_old_checkout_redirects_to_cart_without_creating_order(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"))
        self.assertRedirects(response, reverse("training_cart"))
        self.assertEqual(len(self.client.session["training_cart"]), 1)
        self.assertFalse(TrainingOrder.objects.exists())

    def test_checkout_requires_post_and_nonempty_cart(self):
        self.assertEqual(self.client.get(reverse("training_checkout")).status_code, 405)
        response = self.client.post(reverse("training_checkout"))
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        self.assertFalse(TrainingOrder.objects.exists())
        self.assertNotContains(self.client.get(reverse("training_cart")), "1330686349")

    def test_existing_full_price_order_keeps_original_amount(self):
        order = TrainingOrder.objects.create(
            first_name="Alex", last_name="Example", email="alex@example.com",
            total=Decimal("3000.00"),
            items=[{"training": "course", "city": "Durban", "subtotal": "3000.00"}],
        )
        response = self.client.get(reverse("training_payment", args=[order.token]))
        self.assertContains(response, "R3000.00")
        self.assertNotContains(response, "remaining R2500.00")

    def test_empty_submission_shows_errors(self):
        response = self.client.post(reverse("training_shop"), {})
        self.assertTrue(response.context["form"].errors)

    @override_settings(PAYFAST_MERCHANT_ID="")
    def test_eft_cart_does_not_require_payfast_configuration(self):
        self.add_item()
        self.assertContains(self.client.get(reverse("training_cart")), "1330686349")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_pending_legacy_order_does_not_offer_another_payment(self):
        order = TrainingOrder.objects.create(total=Decimal("500.00"), items=[])
        page = self.client.get(reverse("training_payment", args=[order.token]))
        self.assertContains(page, "contact")
        self.assertContains(page, "1330686349")
        self.assertNotContains(page, "Pay with PayFast")

    def test_return_does_not_confirm_payment(self):
        order = self.create_order()
        response = self.client.get(reverse("training_payment_return", args=[order.token]))
        self.assertContains(response, "Pay by EFT")
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)

    @patch("agency.payfast.urlopen")
    def test_notification_requires_signature_server_validation_and_correct_amount(self, urlopen):
        order = self.create_order()
        fields = [
            ("m_payment_id", str(order.token)),
            ("pf_payment_id", "12345"),
            ("payment_status", "COMPLETE"),
            ("merchant_id", "10000100"),
            ("amount_gross", "3500.00"),
        ]
        urlopen.return_value.__enter__.return_value.read.return_value = b"VALID"
        payload = dict(fields + [("signature", signature(fields, "test passphrase"))])
        invalid = dict(payload, amount_gross="0.01")
        self.assertEqual(self.client.post(reverse("payfast_notify"), invalid).status_code, 400)
        invalid = dict(payload, signature="incorrect")
        self.assertEqual(self.client.post(reverse("payfast_notify"), invalid).status_code, 400)
        urlopen.return_value.__enter__.return_value.read.return_value = b"INVALID"
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)
        urlopen.return_value.__enter__.return_value.read.return_value = b"VALID"
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 200)
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PAID)
        self.assertEqual(order.payfast_payment_id, "12345")

    @patch("agency.payfast.urlopen", side_effect=OSError("PayFast unavailable"))
    def test_notification_network_failure_does_not_confirm_payment(self, urlopen):
        order = self.create_order()
        fields = [
            ("m_payment_id", str(order.token)),
            ("pf_payment_id", "12345"),
            ("payment_status", "COMPLETE"),
            ("merchant_id", "10000100"),
            ("amount_gross", "3500.00"),
        ]
        response = self.client.post(reverse("payfast_notify"), dict(
            fields + [("signature", signature(fields, "test passphrase"))]
        ))
        self.assertEqual(response.status_code, 503)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)
