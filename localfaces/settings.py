import os
from pathlib import Path

import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

# Render sets RENDER=true, so production defaults to DEBUG off (enables WhiteNoise).
DEBUG = os.environ.get("DEBUG", "False" if os.environ.get("RENDER") else "True").lower() == "true"

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG and not os.environ.get("RENDER"):
        raise RuntimeError("SECRET_KEY must be set when DEBUG is False.")
    # Testing-only fallback; set SECRET_KEY in Render's environment for real use.
    SECRET_KEY = "local-development-key-change-before-deploy"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ("127.0.0.1", "localhost")
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "agency",
    "camp.apps.CampConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "localfaces.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "localfaces.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-za"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "private_uploads")))
MEDIA_URL = "private/"

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "camp:dashboard"
LOGOUT_REDIRECT_URL = "camp:apply"

LOCAL_FACES_WHATSAPP_NUMBER = os.environ.get("LOCAL_FACES_WHATSAPP_NUMBER", "27681946795")
EMAIL_BACKEND = "camp.email_backend.ResendEmailBackend"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "info@localfaces.co.za")
PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID", "")
PAYFAST_MERCHANT_KEY = os.environ.get("PAYFAST_MERCHANT_KEY", "")
PAYFAST_PASSPHRASE = os.environ.get("PAYFAST_PASSPHRASE", "")
PAYFAST_SITE_URL = os.environ.get("PAYFAST_SITE_URL", "")
PAYFAST_SANDBOX = os.environ.get("PAYFAST_SANDBOX", "True").lower() == "true"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
    SECURE_CONTENT_TYPE_NOSNIFF = True
