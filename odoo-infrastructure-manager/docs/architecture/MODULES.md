# Creating a Business Module

Every business module lives under `apps/modules/<module_name>/` and is fully
self-contained. Copy `apps/modules/example/` as the starting point — it is the
reference implementation.

## 1. Module Structure

```
apps/modules/<module_name>/
├── __init__.py            # default_app_config = "apps.modules.<module_name>.apps.<Name>Config"
├── apps.py                # app config + ready() registers permissions
├── admin.py               # admin registration
├── urls.py                # app_name + API routes (mounted under /api/...)
├── migrations/
├── models/
│   ├── __init__.py
│   └── <model>.py         # one file per model
├── repositories/
│   ├── __init__.py
│   └── <name>_repository.py   # extends apps.core.repositories.BaseRepository
├── services/
│   ├── __init__.py
│   └── <name>_service.py      # create/update/delete/list, transaction.atomic + audit
├── serializers/
│   ├── __init__.py
│   └── <name>_serializer.py   # serialize_* helpers
├── forms/
│   ├── __init__.py
│   └── <name>_form.py         # optional ModelForm for server-rendered pages
├── permissions/
│   └── __init__.py            # PERMISSIONS dict + GROUPS dict
├── views/
│   ├── __init__.py
│   └── <name>_views.py        # function views using api_response/api_error
└── tests/
    ├── __init__.py
    └── test_<name>.py
```

## 2. Registration Steps

1. Add the app to `INSTALLED_APPS` in `config/settings/base.py`:
   ```python
   "apps.modules.<module_name>",
   ```
2. Mount the module routes in `config/api_urls.py`:
   ```python
   path("modules/<module_name>/", include("apps.modules.<module_name>.urls")),
   ```
3. Create and run migrations:
   ```bash
   python manage.py makemigrations <module_name>
   python manage.py migrate
   ```
4. Verify permission registration (auto-registered in `apps.py` → `ready()`):
   ```bash
   python manage.py shell -c "from apps.core.permissions import PERMISSION_REGISTRY; print(PERMISSION_REGISTRY)"
   ```

## 3. Permissions Convention

`permissions/__init__.py` exports two dicts:

```python
PERMISSIONS = {
    "<module>_view": "View {Module}",
    "<module>_manage": "Manage {Module}",
    "nav_<module>": "Show {Module} in navigation",
}
GROUPS = {
    "<module>": ["<module>_view", "<module>_manage", "nav_<module>"],
}
```

The `ready()` method in `apps.py` merges these into the global
`PERMISSION_REGISTRY`, so they become available to the admin, group management,
and permission checks without extra wiring.

## 4. Service Layer Rules

- All create/update/delete operations run inside `transaction.atomic()`.
- Business rules raise `BusinessRuleError`; duplicates raise `ConflictError`;
  validation errors raise `ValidationError` (all from `apps.core.utils.exceptions`).
- Important actions are recorded via `log_audit(...)`.
- No business logic goes into views — views only call services and shape the
  response.

## 5. API Views

Use the helpers from `apps.core.utils.http` and the decorators from
`apps.core.utils.decorators`:

```python
from apps.core.utils.http import api_response, api_error, exception_to_response
from apps.core.utils.decorators import api_login_required, api_permission_required
```

Every endpoint returns the unified response envelope
(see `docs/api/API.md`). Protect endpoints with `api_login_required` and
`api_permission_required("<module>_manage", ...)` using the module's
permission codes.

## 6. Removing a Module

1. Delete `apps/modules/<module_name>/`.
2. Remove its entry from `INSTALLED_APPS` and `config/api_urls.py`.
3. Run `python manage.py makemigrations --check` to confirm no dangling deps.

No Core or Accounts code references business modules, so removal is safe.
