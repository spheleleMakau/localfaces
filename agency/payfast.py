import hashlib
import hmac
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings


def base_url():
    return "https://sandbox.payfast.co.za" if settings.PAYFAST_SANDBOX else "https://www.payfast.co.za"


def parameter_string(pairs):
    return urlencode(pairs).replace("~", "%7E")


def signature(pairs, passphrase):
    pairs = list(pairs)
    if passphrase:
        pairs.append(("passphrase", passphrase.strip()))
    return hashlib.md5(parameter_string(pairs).encode("utf-8")).hexdigest()


def local_sandbox():
    url = urlparse(settings.PAYFAST_SITE_URL)
    return (
        settings.DEBUG
        and settings.PAYFAST_SANDBOX
        and url.scheme == "http"
        and url.hostname in ("localhost", "127.0.0.1")
    )


def valid_notification(pairs, supplied_signature):
    if not re.fullmatch(r"[0-9a-f]{32}", supplied_signature):
        return False
    expected = signature(pairs, settings.PAYFAST_PASSPHRASE)
    if not hmac.compare_digest(expected, supplied_signature):
        return False
    data = parameter_string(pairs).encode("utf-8")
    request = Request(f"{base_url()}/eng/query/validate", data=data)
    with urlopen(request, timeout=10) as response:
        return response.read(64).strip() == b"VALID"
