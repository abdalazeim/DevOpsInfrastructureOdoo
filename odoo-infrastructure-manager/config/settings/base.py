import os
from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ""),
    DATABASE_URL=(str, ""),
    DJANGO_ALLOWED_HOSTS=(str, ""),
    CSRF_TRUSTED_ORIGINS=(str, ""),
    CORS_ALLOWED_ORIGINS=(str, ""),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(bool, True),
    DEFAULT_FROM_EMAIL=(str, ""),
    RATE_LIMIT_LOGIN=(str, "10/m"),
    RATE_LIMIT_API=(str, "60/m"),
    DJANGO_SEED_ADMIN=(bool, False),
    DJANGO_ADMIN_USERNAME=(str, "admin"),
    DJANGO_ADMIN_EMAIL=(str, "admin@localhost"),
    DJANGO_ADMIN_PASSWORD=(str, ""),
    LANGUAGE_CODE=(str, "ar"),
    APP_FONT_FAMILY=(str, "Cairo"),
    ENABLE_DOMAIN_SAMPLES=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")

SECRET_KEY = env("SECRET_KEY") or os.environ.get("SECRET_KEY", "")

ALLOWED_HOSTS = [
    h.strip()
    for h in (env("DJANGO_ALLOWED_HOSTS") or "localhost,127.0.0.1").split(",")
    if h.strip()
]

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "apps.core",
    "apps.accounts",
    "apps.modules.example",
    "apps.infrastructure",
]

# Optional domain samples stay outside the core app package so Django's test
# discovery and default migrations remain domain-neutral.
ENABLE_DOMAIN_SAMPLES = env("ENABLE_DOMAIN_SAMPLES")
if ENABLE_DOMAIN_SAMPLES:
    INSTALLED_APPS.append("examples.transport")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.security.InputSanitizationMiddleware",
    "apps.core.middleware.rate_limit.RateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "apps.core.middleware.language.LanguageSwitchMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.jwt_auth.JWTAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.security.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "apps.core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ==============================================================================
# DATABASE
# Local default is SQLite (db.sqlite3 in the project root) so the system runs
# out of the box. When DATABASE_URL is provided (PostgreSQL/Neon, production),
# it is used instead — Single Source of Truth.
# ==============================================================================

import dj_database_url  # noqa: E402

DATABASE_URL = env("DATABASE_URL") or os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        ),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ==============================================================================
# PostgreSQL search_path fix
# Neon pooled connections can start with an empty search_path, which makes
# unqualified table lookups fail intermittently with "relation does not exist".
# Force "public" on every new PostgreSQL connection (after connect, not as a
# startup option, which Neon's pooler rejects).
# ==============================================================================
from django.db.backends.signals import connection_created  # noqa: E402


def _force_public_search_path(sender, connection, **kwargs):
    if connection.vendor != "postgresql":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO public")
    except Exception:
        pass


connection_created.connect(
    _force_public_search_path, dispatch_uid="force_public_search_path"
)

# ==============================================================================
# AUTH
# ==============================================================================
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ==============================================================================
# DRF (Django REST Framework)
# Session auth is used by default; every DRF viewset requires authentication.
# All errors flow through the unified envelope handler so API responses are
# consistent across the whole template.
# ==============================================================================
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.EnvelopePageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.utils.http.drf_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

# ==============================================================================
# JWT (Simple JWT) - for Android/Mobile clients
# ==============================================================================
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": (
        "rest_framework_simplejwt.authentication.default_user_authentication_rule"
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=60),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=7),
}

# ==============================================================================
# drf-spectacular (OpenAPI / Swagger) - API documentation
# ==============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "Enterprise Template API",
    "DESCRIPTION": "Reusable Django enterprise starter template API for any business system.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ActionType": "apps.core.constants.AuditAction",
        "SortDirection": "apps.core.constants.SortDirection",
    },
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "expandResponses": ["200", "201", "400"],
    },
    "POSTPROCESSING_HOOKS": [],
    "PREPROCESSING_HOOKS": [],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "SessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "sessionid",
            },
        },
    },
    "SECURITY": [
        {"BearerAuth": []},
        {"SessionAuth": []},
    ],
    "TAGS": [
        {"name": "auth", "description": "Authentication (login, logout, status, JWT)"},
        {"name": "users", "description": "User management"},
        {"name": "roles", "description": "System roles"},
        {"name": "groups", "description": "User groups"},
        {"name": "permissions", "description": "Permissions management"},
        {"name": "dashboard", "description": "Dashboard statistics"},
        {"name": "audit", "description": "Audit logs"},
        {"name": "backup", "description": "Backup & restore"},
        {"name": "settings", "description": "System settings"},
        {"name": "modules", "description": "Business modules"},
        {"name": "sync", "description": "Offline-first sync (push/pull)"},
        {"name": "health", "description": "Health checks"},
    ],
}

# ==============================================================================
# DEFAULT ADMIN SEEDING
# Creates an initial superuser on post_migrate ONLY when explicitly enabled
# via DJANGO_SEED_ADMIN=true (never automatic, so production stays secure).
# ==============================================================================
SEED_DEFAULT_ADMIN = env("DJANGO_SEED_ADMIN")
DEFAULT_ADMIN_USERNAME = env("DJANGO_ADMIN_USERNAME")
DEFAULT_ADMIN_EMAIL = env("DJANGO_ADMIN_EMAIL")
DEFAULT_ADMIN_PASSWORD = env("DJANGO_ADMIN_PASSWORD")

# ==============================================================================
# INTERNATIONALIZATION
# Arabic is the default (RTL); English (LTR) is fully supported. The active
# language can be switched via the ``?lang=`` query param (LocaleMiddleware
# stores it in the session) or overridden with LANGUAGE_CODE in .env.
# ==============================================================================
LANGUAGE_CODE = env("LANGUAGE_CODE")
LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "app_language"
LANGUAGE_COOKIE_AGE = None

TIME_ZONE = env("TZ", default="UTC")
USE_I18N = True
USE_TZ = True

# ==============================================================================
# UI / FONTS
# Default Arabic font family (Cairo or Tajawal). Individual pages/templates can
# override; the value is exposed to templates via a context processor.
# ==============================================================================
APP_FONT_FAMILY = env("APP_FONT_FAMILY")

SITE_TITLE = env("SITE_TITLE", default="واجهة التطبيق")
SITE_SUBTITLE = env("SITE_SUBTITLE", default="Enterprise Starter")

# ==============================================================================
# STATIC & MEDIA FILES
# ==============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# DEFAULT PRIMARY KEY FIELD
# ==============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# BACKUP
# ==============================================================================
BACKUP_DIR = BASE_DIR / "backup"
MAX_BACKUPS = 10
BACKUP_COOLDOWN_SECONDS = 60

# ==============================================================================
# RATE LIMITING
# ==============================================================================
RATE_LIMIT_LOGIN = env("RATE_LIMIT_LOGIN")
RATE_LIMIT_API = env("RATE_LIMIT_API")

# ==============================================================================
# EMAIL
# ==============================================================================
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env("EMAIL_PORT")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env("EMAIL_USE_TLS")
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ==============================================================================
# LOGGING
# Professional logging architecture with separated application / error /
# security streams and automatic rotation.
#
#   logs/application.log  -> INFO+ application & API events
#   logs/error.log        -> ERROR+ database / request / unexpected errors
#   logs/security.log     -> WARNING+ authentication & authorization events
#
# Usage from business code:
#   import logging
#   logger = logging.getLogger("apps.api")      # application stream
#   security_logger = logging.getLogger("apps.security")  # security stream
# ==============================================================================
_LOG_DIR = BASE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {module}:{lineno} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "security": {
            "format": "{asctime} {levelname} [{name}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO" if DEBUG else "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "application_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOG_DIR / "application.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOG_DIR / "error.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "verbose",
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOG_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "security",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "apps.api": {
            "handlers": ["console", "application_file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "apps.security": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
