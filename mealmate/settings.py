"""
Django settings for Eatzo (formerly mealmate) project.
Local-development friendly + production ready.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Optional python-decouple
try:
    from decouple import config
    USE_DECOUPLE = True
except ImportError:
    USE_DECOUPLE = False


BASE_DIR = Path(__file__).resolve().parent.parent


def get_env_variable(var_name, default=None):
    if USE_DECOUPLE:
        return config(var_name, default=default)
    return os.environ.get(var_name, default)


def get_bool_env_variable(var_name, default=False):
    value = get_env_variable(var_name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# =========================
# CORE SETTINGS
# =========================

DEBUG = get_bool_env_variable("DEBUG", False)

SECRET_KEY = get_env_variable("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")
    SECRET_KEY = "django-insecure-local-development-only"
elif not DEBUG and (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
    or SECRET_KEY == "your-secret-key-here-change-in-production"
    or SECRET_KEY.startswith("replace-with-")
):
    raise ImproperlyConfigured(
        "Set SECRET_KEY to a unique random value of at least 50 characters "
        "when DEBUG is False."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in get_env_variable("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
if not DEBUG and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain '*' when DEBUG is False.")
if not DEBUG and any(
    host.lower() in {"yourdomain.com", "www.yourdomain.com"}
    for host in ALLOWED_HOSTS
):
    raise ImproperlyConfigured("Replace the sample ALLOWED_HOSTS values before deployment.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in get_env_variable("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

EMAIL_BACKEND = get_env_variable(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = get_env_variable("EMAIL_HOST", "localhost")
EMAIL_PORT = int(get_env_variable("EMAIL_PORT", "25"))
EMAIL_USE_TLS = get_bool_env_variable("EMAIL_USE_TLS", False)
EMAIL_HOST_USER = get_env_variable("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = get_env_variable("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = get_env_variable("DEFAULT_FROM_EMAIL", "webmaster@localhost")

RAZORPAY_KEY_ID = get_env_variable("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = get_env_variable("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = get_env_variable("RAZORPAY_WEBHOOK_SECRET", "")

SESSION_COOKIE_AGE = 86400
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECURE_SSL_REDIRECT = get_bool_env_variable("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(get_env_variable("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = get_bool_env_variable(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = get_bool_env_variable("SECURE_HSTS_PRELOAD", False)
SESSION_COOKIE_SECURE = get_bool_env_variable("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = get_bool_env_variable("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if get_bool_env_variable("TRUST_X_FORWARDED_PROTO", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# =========================
# APPLICATIONS
# =========================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "delivery.apps.DeliveryConfig",
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
]

ROOT_URLCONF = "mealmate.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "delivery" / "Templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mealmate.wsgi.application"


# =========================
# DATABASE (SQLite local)
# =========================

if get_bool_env_variable("USE_POSTGRES", False):
    database_password = get_env_variable("DB_PASSWORD", "")
    if not DEBUG and (
        len(database_password) < 16
        or database_password.lower()
        in {"your-db-password", "replace-with-a-strong-database-password"}
    ):
        raise ImproperlyConfigured(
            "Set DB_PASSWORD to a strong value of at least 16 characters."
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": get_env_variable("DB_NAME", "eatzo"),
            "USER": get_env_variable("DB_USER", "eatzo"),
            "PASSWORD": database_password,
            "HOST": get_env_variable("DB_HOST", "localhost"),
            "PORT": get_env_variable("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(get_env_variable("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# =========================
# AUTH
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =========================
# LOCALIZATION
# =========================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# =========================
# STATIC / MEDIA
# =========================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "delivery" / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================
# LOGGING
# =========================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {"handlers": ["console"], "level": get_env_variable("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": get_env_variable("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "eatzo-cache",
    }
}

CELERY_BROKER_URL = get_env_variable("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = get_env_variable("CELERY_RESULT_BACKEND", "")


# =========================
# CUSTOM SETTINGS
# =========================

MIN_ORDER_AMOUNT = float(get_env_variable("MIN_ORDER_AMOUNT", "0"))
MAX_CART_ITEMS = int(get_env_variable("MAX_CART_ITEMS", "50"))
