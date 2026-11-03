"""Test settings: fast in-memory SQLite so unit tests run quickly.

Run with: python manage.py test --settings=config.settings.test
"""

from .development import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Keep tests deterministic: never seed default admin in the test database.
SEED_DEFAULT_ADMIN = False
