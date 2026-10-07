from uuid import UUID

from .models import Application


def application_share_token(application):
    return application.share_token


def get_shared_application(token):
    try:
        share_token = token if isinstance(token, UUID) else UUID(str(token))
        return Application.objects.prefetch_related("photos").get(
            share_token=share_token
        )
    except (Application.DoesNotExist, TypeError, ValueError, AttributeError):
        return None
