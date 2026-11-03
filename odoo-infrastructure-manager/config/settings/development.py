from .base import *  # noqa: F401, F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "django-insecure-dev-key-do-not-use-in-production"

# base.py builds SIMPLE_JWT before this development-only fallback is selected.
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
X_FRAME_OPTIONS = "SAMEORIGIN"
CORS_ALLOW_ALL_ORIGINS = True
