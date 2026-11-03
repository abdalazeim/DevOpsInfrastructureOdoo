"""
Desktop (PyInstaller-frozen) settings.
Inherits from base and overrides paths for frozen deployment.
"""

import secrets
import sys
from pathlib import Path

from .base import *  # noqa: F401, F403


def is_frozen():
    return getattr(sys, "frozen", False)


def get_bundle_dir():
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_app_dir():
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BUNDLE_DIR = get_bundle_dir()

BASE_DIR = get_app_dir()

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    _secret_path = BASE_DIR / ".desktop-secret-key"
    try:
        SECRET_KEY = _secret_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        SECRET_KEY = secrets.token_urlsafe(64)
        _secret_path.write_text(SECRET_KEY, encoding="utf-8")

# The desktop key can be generated after base.py initialized JWT settings.
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405

if not DATABASE_URL:  # noqa: F405
    DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

TEMPLATES[0]["DIRS"] = [  # noqa: F405
    Path(str(d).replace(str(get_app_dir()), str(BUNDLE_DIR)))
    for d in TEMPLATES[0]["DIRS"]  # noqa: F405
]

STATICFILES_DIRS = [BUNDLE_DIR / "static"]
if (BUNDLE_DIR / "staticfiles").exists():
    STATIC_ROOT = BUNDLE_DIR / "staticfiles"
else:
    STATIC_ROOT = BASE_DIR / "staticfiles"

# Database inherits from base.py — SQLite (db.sqlite3) by default.
# Optional: set DATABASE_URL in .env to switch to PostgreSQL.

BACKUP_DIR = BASE_DIR / "backup"
MEDIA_ROOT = BASE_DIR / "media"
_LOG_DIR_DESKTOP = BASE_DIR / "logs"
_LOG_DIR_DESKTOP.mkdir(exist_ok=True)
LOGGING["handlers"]["application_file"]["filename"] = str(  # noqa: F405
    _LOG_DIR_DESKTOP / "application.log"
)
LOGGING["handlers"]["error_file"]["filename"] = str(  # noqa: F405
    _LOG_DIR_DESKTOP / "django-error.log"
)
LOGGING["handlers"]["security_file"]["filename"] = str(  # noqa: F405
    _LOG_DIR_DESKTOP / "security.log"
)

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
X_FRAME_OPTIONS = "SAMEORIGIN"
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = []
