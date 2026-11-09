import json
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not settings.RESEND_API_KEY:
            raise ImproperlyConfigured("RESEND_API_KEY is required for application email delivery.")
        sent = 0
        for message in email_messages:
            payload = json.dumps({
                "from": message.from_email,
                "to": message.to,
                "subject": message.subject,
                "text": message.body,
            }).encode("utf-8")
            headers = {
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            }
            if "Idempotency-Key" in message.extra_headers:
                headers["Idempotency-Key"] = message.extra_headers["Idempotency-Key"]
            request = Request("https://api.resend.com/emails", data=payload, headers=headers, method="POST")
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict) or not result.get("id"):
                raise ValueError("Resend did not return an email ID.")
            sent += 1
        return sent
