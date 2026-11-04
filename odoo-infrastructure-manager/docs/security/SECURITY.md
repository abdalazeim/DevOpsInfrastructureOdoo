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
| `LanguageSwitchMiddleware` | Enforces the active English-only interface |
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

- Permission codes are declared in the Accounts catalog and registered by modules.
- A global `PERMISSION_REGISTRY` merges all module permissions at startup.
- `has_permission(user, *perm_codes)` (`apps/accounts/services/permission_service.py`)
  resolves direct user, application-group, system-role, and Django auth-group grants.
- Inactive user accounts and inactive profiles have no effective grants. Permission
  assignment APIs reject unknown codes and reject delegation beyond the actor's own
  grants; only a superuser may seed the full default role set.
- API views use `api_login_required` (401) and `api_permission_required` (403)
  decorators from `apps/core/utils/decorators.py`.

## 6. Credential Encryption

`apps.security.Credential` stores SSH passwords, SSH private keys, and provider
tokens as Fernet ciphertext. The independent `CREDENTIAL_ENCRYPTION_KEY` must
be a valid Fernet key and must not be committed. The local development key is
kept in the ignored `.env` file with mode `0600`; production must provide it via
a protected secret store. Without a valid key, credential creation is disabled
and encryption fails closed. Credential lists and audit records contain metadata
only; the secret is never rendered or serialized.

The Global Settings quick-connect form accepts a server name, address, SSH login,
password and port. It creates the host record and an encrypted SSH credential in
one database transaction, then probes SSH when the actor also has `server.connect`.
Local application hosts use direct collection and do not store an SSH credential.
SSH still rejects unknown or changed host keys; configure trusted host keys for
the web/worker service account before expecting a probe to succeed.

To rotate keys without losing access to existing ciphertext:

1. Set the new primary `CREDENTIAL_ENCRYPTION_KEY` and the old key in
   `CREDENTIAL_ENCRYPTION_KEY_FALLBACKS`.
2. Run `python manage.py rotate_credential_keys` and verify it reports the
   number of encrypted records processed.
3. Remove the old key from the fallback list after successful rotation and
   retain a protected recovery copy according to the deployment's key policy.

SSH probes reject unknown host keys, use bounded timeouts, invoke only the fixed
`uname -srm` metadata probe, and redact exception details before returning them.
Do not weaken host-key policy to make an untrusted host connect.

Linux service restart is limited to a currently running systemd unit from a fresh
local discovery snapshot. It requires `linux.service.restart`, a typed `RESTART`
confirmation, and task dispatch through the configured Celery worker. The adapter
uses a fixed `systemctl restart <unit>` call and verifies the unit is active after
the restart; arbitrary shell commands are never accepted.

## 7. Logging

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

## 8. Audit Log

Generic `AuditLog` model in `apps/core/models/audit_log.py` records:
user, action, module, object, timestamp, IP, old value, new value.

Actions: `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `APPROVE`, `REJECT`.
It is generic (not tied to any business domain); services call the shared
`log_audit(...)` helper inside their `transaction.atomic()` block.

## 9. Attack Vectors

- **CSRF** — default Django CSRF middleware + `CsrfViewMiddleware`; API write
  endpoints accept the CSRF cookie/token.
- **XSS** — template auto-escaping + `InputSanitizationMiddleware` +
  `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options).
- **SQL injection** — Django ORM everywhere; no raw SQL except the fixed
  `search_path` and health `SELECT 1`.
- **Brute force** — rate limiting on login (`RATE_LIMIT_LOGIN=10/m`).
- **Session** — session-based auth with secure-cookie flags in production.

## 10. Production Checklist

1. `DEBUG=False`
2. `SECRET_KEY` set to a long random value (env only)
3. `DJANGO_ALLOWED_HOSTS` locked to real hosts
4. `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` set
5. `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`,
   `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS` set
6. `DATABASE_URL` with `sslmode=require`
7. `DJANGO_SEED_ADMIN` left `False`; create the admin manually
8. Email backend configured (not console)
9. `CREDENTIAL_ENCRYPTION_KEY` stored separately from `SECRET_KEY`; fallback
   keys are removed after a verified rotation
