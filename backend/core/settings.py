# =========================================================
# Core Project Settings
# =========================================================

from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "").split(",")
# CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="https://*.up.railway.app").split(",")

# Support for proxy-based HTTPS
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# WhiteNoise stability: prevent crash on missing static files
WHITENOISE_MANIFEST_STRICT = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    # Local apps
    "common",
    "account",
    "master",
    "journal",
    "ledger",
    "report",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.rbac",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DB_USER = config("POSTGRES_USER")
DB_PASS = config("POSTGRES_PASSWORD")
DB_HOST = config("POSTGRES_HOST")
DB_PORT = config("POSTGRES_PORT")
DB_NAME = config("POSTGRES_DB")

DEFAULT_DATABASE_URL = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=DEFAULT_DATABASE_URL),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
_STATIC_DIR = BASE_DIR / "static"
_STATIC_DIR.mkdir(exist_ok=True)
STATICFILES_DIRS = [_STATIC_DIR]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Messages
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-error",
}
