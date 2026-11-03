from .base import *  # noqa: F401, F403

DEBUG = False

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required in production!")

_allowed_hosts = env("DJANGO_ALLOWED_HOSTS").strip()
if not _allowed_hosts:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain the production host names.")
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(",") if host.strip()]
if "*" in ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must not contain '*'.")

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("DATABASE_URL must point to PostgreSQL in production.")

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = max(env("SECURE_HSTS_SECONDS"), 31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD", default=False)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# The server-rendered SPA reads the CSRF cookie for its X-CSRFToken header.
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 86400

_trusted = env("CSRF_TRUSTED_ORIGINS")
if _trusted:
    CSRF_TRUSTED_ORIGINS = _trusted.split(",")
_cors = env("CORS_ALLOWED_ORIGINS")
if _cors:
    CORS_ALLOWED_ORIGINS = _cors.split(",")
    CORS_ALLOW_CREDENTIALS = True
