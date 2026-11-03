# Security

## 1. Principles

- `DEBUG=False` in production; the system must never run with development
  settings in production (`manage.py` selects `config.settings.production`
  automatically when `PORT`/`RENDER` is set).
- No passwords, secret keys, API keys or tokens are stored in Git.
  Configuration lives in `.env` (git-ignored); `.env.example` documents keys.

## 2. Django Security Defaults

- `AUTH_USER_MODEL = "accounts.User"` — custom user model.
- Full password validators enabled (similarity, minimum length, common, numeric).
- Production settings enable:
  - `SECURE_SSL_REDIRECT` (HTTP→HTTPS)
  - `SECURE_HSTS_SECONDS` (HSTS)
  - `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`
  - `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` (from env)
- `XFrameOptionsMiddleware` and `SecurityHeadersMiddleware` add clickjacking
  and security headers.
- WhiteNoise serves static files safely in production.

## 3. Core Security Middleware

Middleware stack (in order, `config/settings/base.py`):

| Middleware | Purpose |
|------------|---------|
| `InputSanitizationMiddleware` | Sanitize/clean incoming input |
| `RateLimitMiddleware` | Request rate limiting (login + API) |
| `LanguageSwitchMiddleware` | `?lang=` switch (session/cookie) |
| `SecurityHeadersMiddleware` | Security response headers |

## 4. Authentication Events

All authentication and authorization events are logged through
`log_security_event(event, user, request, level, extra)` from
`apps/core/utils/logging.py`:

- `login_failed` — wrong credentials
- `login_success` (INFO) — successful login
- `login_disabled_account` — disabled account attempt
- `logout` (INFO)
- `anonymous_access_denied` — unauthenticated API access
- `permission_denied` — authenticated user without required permission

Events carry `user=`, `ip=`, `path=` and arbitrary `extra` context and land in
`logs/security.log` (plus console).

## 5. Authorization Model

- Role/group based permissions declared per module in `permissions/__init__.py`.
- A global `PERMISSION_REGISTRY` merges all module permissions at startup.
- `has_permission(user, *perm_codes)` (`apps/accounts/services/permission_service.py`)
  checks group membership.
- API views use `api_login_required` (401) and `api_permission_required` (403)
  decorators from `apps/core/utils/decorators.py`.

## 6. Logging

```
logs/
├── application.log    # INFO+ application & API events (rotated, 5MB x 5)
├── error.log          # ERROR+ request/db/unexpected errors
└── security.log       # WARNING+ authentication/authorization events
```

Loggers: `django`, `django.request`, `django.db.backends`, `django.security`,
`apps`, `apps.api`, `apps.security`. In production, `ERROR+` events are emailed
to `ADMINS` via `AdminEmailHandler` (`mail_admins`, only when `DEBUG=False`).

Usage from business code:

```python
import logging
logger = logging.getLogger("apps.api")
security_logger = logging.getLogger("apps.security")
```

## 7. Audit Log

Generic `AuditLog` model in `apps/core/models/audit_log.py` records:
user, action, module, object, timestamp, IP, old value, new value.

Actions: `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `APPROVE`, `REJECT`.
It is generic (not tied to any business domain); services call the shared
`log_audit(...)` helper inside their `transaction.atomic()` block.

## 8. Attack Vectors

- **CSRF** — default Django CSRF middleware + `CsrfViewMiddleware`; API write
  endpoints accept the CSRF cookie/token.
- **XSS** — template auto-escaping + `InputSanitizationMiddleware` +
  `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options).
- **SQL injection** — Django ORM everywhere; no raw SQL except the fixed
  `search_path` and health `SELECT 1`.
- **Brute force** — rate limiting on login (`RATE_LIMIT_LOGIN=10/m`).
- **Session** — session-based auth with secure-cookie flags in production.

## 9. Production Checklist

1. `DEBUG=False`
2. `SECRET_KEY` set to a long random value (env only)
3. `DJANGO_ALLOWED_HOSTS` locked to real hosts
4. `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` set
5. `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`,
   `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS` set
6. `DATABASE_URL` with `sslmode=require`
7. `DJANGO_SEED_ADMIN` left `False`; create the admin manually
8. Email backend configured (not console)
