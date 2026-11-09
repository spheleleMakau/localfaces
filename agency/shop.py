import logging
import uuid
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import payfast
from .forms import AddTrainingForm, TRAINING_CITIES
from .models import TrainingOrder
from camp.forms import IndividualTrainingApplicationForm, TrainingApplicationForm
from camp.models import Application, ApplicationEmail
from camp.notifications import send_application_email
from camp.whatsapp import build_application_whatsapp_url

logger = logging.getLogger(__name__)
PRICES = {"course": Decimal("500.00"), "individual": Decimal("1500.00"), "academy": Decimal("1666.67")}
COURSE_BALANCE = Decimal("2500.00")
ACADEMY_INSTALLMENTS = ("1666.67", "1666.66")


def cart_items(request):
    items = []
    for item in request.session.get("training_cart", []):
        price = PRICES[item["training"]]
        quantity = item["hours"] if item["training"] == "individual" else 1
        if item["training"] == "course":
            balance_due = COURSE_BALANCE
        elif item["training"] == "academy":
            balance_due = sum(map(Decimal, ACADEMY_INSTALLMENTS))
        else:
            balance_due = Decimal("0.00")
        whatsapp_url = ""
        if item.get("application_number"):
            application = Application.objects.filter(application_number=item["application_number"]).first()
            if application:
                whatsapp_url = build_application_whatsapp_url(application, request)
        items.append({
            **item,
            "whatsapp_url": whatsapp_url,
            "price": price,
            "subtotal": price * quantity,
            "balance_due": str(balance_due),
            **({"remaining_installments": list(ACADEMY_INSTALLMENTS)} if item["training"] == "academy" else {}),
        })
    return items


def shop(request):
    form = AddTrainingForm(
        request.POST if request.method == "POST" else None,
        initial={"city": request.GET.get("city", "")},
    )
    if request.method == "POST" and form.is_valid():
        item = form.cleaned_data
        cart = request.session.get("training_cart", [])
        if len(cart) >= 100:
            form.add_error(None, "Your cart can contain at most 100 training items.")
        else:
            request.session["pending_training"] = {
                **item, "submission_key": str(uuid.uuid4()),
            }
            return redirect("training_application")
    return render(request, "agency/shop.html", {"form": form})


def training_application(request):
    pending = request.session.get("pending_training")
    if not pending or pending.get("training") not in ("course", "individual"):
        messages.error(request, "Choose training before completing the applicant form.")
        return redirect("training_shop")
    if pending.get("city") not in TRAINING_CITIES:
        messages.error(request, "Training is now available only in Durban, Johannesburg and Cape Town. Please choose your training again.")
        return redirect("training_shop")
    form_class = TrainingApplicationForm if pending["training"] == "course" else IndividualTrainingApplicationForm
    form = form_class(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        initial={"submission_key": pending["submission_key"], "city": pending["city"]},
    )
    if request.method == "POST" and form.is_valid():
        if str(form.cleaned_data["submission_key"]) != pending["submission_key"]:
            form.add_error(None, "This form is no longer current. Please choose your training again.")
        elif len(request.session.get("training_cart", [])) >= 100:
            form.add_error(None, "Your cart can contain at most 100 training items.")
        else:
            try:
                with transaction.atomic():
                    application = Application.objects.filter(submission_key=pending["submission_key"]).first()
                    if application is None:
                        application = form.save()
                        training_selection = {key: pending[key] for key in ("training", "city", "hours")}
                        notification = ApplicationEmail.objects.create(
                            application=application,
                            training_selection=training_selection,
                        )
                    elif application.kind != Application.Kind.TRAINING:
                        raise IntegrityError("Submission key belongs to a different application.")
                    else:
                        notification = ApplicationEmail.objects.filter(application=application).first()
            except (DatabaseError, OSError):
                for image_path in form.saved_photo_paths:
                    try:
                        default_storage.delete(image_path)
                    except OSError:
                        logger.exception("Could not remove an incomplete applicant photo.")
                logger.exception("Could not save a training application.")
                form.add_error(None, "We couldn't save your application because of a technical problem. Please try again, or contact info@localfaces.co.za if the problem continues.")
            else:
                cart = request.session.get("training_cart", [])
                item = {key: value for key, value in pending.items() if key != "submission_key"}
                item["application_number"] = application.application_number
                cart.append(item)
                request.session["training_cart"] = cart
                del request.session["pending_training"]
                messages.success(request, "Training and applicant details added to your cart.")
                if notification and notification.status != ApplicationEmail.Status.SENT:
                    send_application_email(notification, request)
                return redirect("training_cart")
    return render(request, "agency/training_application.html", {"form": form, "selection": pending})


@require_GET
def academy_opportunity(request):
    return render(request, "agency/academy_opportunity.html")


def cart(request):
    items = cart_items(request)
    application_numbers = [
        item.get("application_number") for item in items if item["training"] in ("course", "individual")
    ]
    valid_applications = set(Application.objects.filter(
        kind=Application.Kind.TRAINING, application_number__in=application_numbers,
    ).values_list("application_number", flat=True))
    needs_application = any(number not in valid_applications for number in application_numbers)
    response = render(request, "agency/cart.html", {
        "items": items,
        "total": sum((item["subtotal"] for item in items), Decimal("0.00")),
        "needs_application": needs_application,
    })
    response["Cache-Control"] = "private, no-store"
    return response


@require_POST
def remove_item(request, index):
    items = request.session.get("training_cart", [])
    if index >= len(items):
        return HttpResponseBadRequest("Invalid cart item.")
    items.pop(index)
    request.session["training_cart"] = items
    return redirect("training_cart")


def configured():
    url = urlparse(settings.PAYFAST_SITE_URL)
    return bool(settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_MERCHANT_KEY and (url.scheme == "https" or payfast.local_sandbox()) and url.hostname and not url.username and not url.password and not url.path.rstrip("/") and not url.query and not url.fragment)


@require_POST
def checkout(request):
    messages.info(request, "Payment instructions are now shown in your cart.")
    return redirect("training_cart")


def payment(request, token):
    order = get_object_or_404(TrainingOrder, token=token)
    response = render(request, "agency/payment.html", {"order": order})
    response["Cache-Control"] = "private, no-store"
    return response


def payment_return(request, token, cancelled=False):
    return payment(request, token)


@csrf_exempt
@require_POST
def notify(request):
    if not configured():
        return HttpResponse(status=503)
    if any(len(values) != 1 for _, values in request.POST.lists()):
        return HttpResponseBadRequest("Invalid notification.")
    pairs = []
    found_signature = False
    for key, value in request.POST.items():
        if key == "signature":
            found_signature = True
            continue
        if found_signature:
            return HttpResponseBadRequest("Invalid notification.")
        pairs.append((key, value))
    data = dict(pairs)
    try:
        token = uuid.UUID(data.get("m_payment_id", ""))
        amount = Decimal(data.get("amount_gross", ""))
        if not amount.is_finite():
            raise InvalidOperation
    except (ValueError, InvalidOperation):
        return HttpResponseBadRequest("Invalid notification.")
    order = TrainingOrder.objects.filter(token=token).first()
    if (not order or data.get("merchant_id") != settings.PAYFAST_MERCHANT_ID
            or amount != order.total or data.get("payment_status") != "COMPLETE"
            or not data.get("pf_payment_id") or not found_signature):
        return HttpResponseBadRequest("Invalid notification.")
    try:
        valid = payfast.valid_notification(pairs, request.POST["signature"])
    except (OSError, URLError):
        logger.exception("Could not verify PayFast notification for order %s", token)
        return HttpResponse(status=503)
    if not valid:
        logger.warning("Rejected PayFast notification for order %s", token)
        return HttpResponseBadRequest("Invalid notification.")
    with transaction.atomic():
        order = TrainingOrder.objects.select_for_update().get(pk=order.pk)
        if order.status == TrainingOrder.Status.PAID and order.payfast_payment_id != data["pf_payment_id"]:
            logger.error("Conflicting PayFast transaction for order %s", token)
            return HttpResponseBadRequest("Conflicting transaction.")
        order.status = TrainingOrder.Status.PAID
        order.payfast_payment_id = data["pf_payment_id"]
        order.save(update_fields=["status", "payfast_payment_id"])
    return HttpResponse("OK")
