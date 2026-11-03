# Testing Strategy

## 1. Overview

Tests are grouped at two levels:

- **Per-module tests** — each business module ships its own `tests/` directory
  (e.g. `apps/modules/example/tests/test_example.py`).
- **Global test suites** — cross-cutting suites under `tests/`:

```
tests/
├── unit/            # isolated unit tests (services, validators)
├── integration/     # component integration & smoke tests
└── e2e/             # end-to-end API flows
```

## 2. Running Tests

```bash
python manage.py test                              # all tests (DiscoverRunner)
python manage.py test apps.modules.example         # one app's tests
python manage.py test apps.modules.example.tests.test_example.ModelTests
python manage.py test tests.unit                   # global unit suite
```

`config/settings/test.py` inherits the development settings and uses a fast
test database (SQLite), so the suite runs quickly without PostgreSQL.

> Note: the project DB (`db.sqlite3`) is not migrated by default; the test
> runner creates an isolated temporary database, so tests never touch real data.

## 3. Test Categories

| Category | Covers |
|----------|--------|
| Model tests | `__str__`, field defaults, uniqueness, ordering, indexes |
| Service tests | business rules, transactions, conflict/not-found paths, audit logging |
| API tests | endpoint status codes, response envelope shape, auth/permission denial, validation errors |
| Integration | end-to-end flows across views, services and repositories |
| E2E | authenticated smoke passes over every list/create/update/delete endpoint |

## 4. Conventions

- File name: `test_<area>.py`; classes like `ModelTests`, `ApiTests`.
- Use Django's `TestCase`; the `client` handles CSRF automatically in tests.
- API responses are asserted against the unified envelope
  (`success`, `message`, `data`, `errors`).
- Each module must keep its own tests green in isolation, so a module can be
  removed without breaking the rest of the suite.

## 5. Full Verification Before Delivery

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
python scripts/verify_api.py
python scripts/check_static_refs.py
```
