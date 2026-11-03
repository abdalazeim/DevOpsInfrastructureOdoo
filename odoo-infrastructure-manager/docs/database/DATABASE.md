# Database Architecture

## 1. Strategy

The database is independent of any specific project. The connection is driven by
a single source of truth — `DATABASE_URL`:

| Environment | Database | Configuration |
|-------------|----------|---------------|
| Development (default) | SQLite | `db.sqlite3` in project root (no config needed) |
| Production / Render | PostgreSQL 16+ | `DATABASE_URL` in `.env` / dashboard |
| Cloud (Neon) | PostgreSQL-compatible | `DATABASE_URL` with `sslmode=require` |
| Tests | SQLite (in-memory) | `config.settings.test` |

```python
# config/settings/base.py
DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600,
                   conn_health_checks=True, ssl_require=not DEBUG)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                             "NAME": BASE_DIR / "db.sqlite3"}}
```

## 2. Connection Settings

- `conn_max_age=600` — persistent connections in production.
- `conn_health_checks=True` — broken connections are detected and recreated.
- `ssl_require=not DEBUG` — SSL enforced outside debug mode.
- PostgreSQL `search_path` is forced to `public` on connect (Neon-compatible,
  fixes "relation does not exist" on pooled connections).

## 3. Models & Migrations

- All models extend `BaseModel` from `apps/core/models/base.py`
  (`created_at`, `updated_at`, `created_by`, `updated_by`).
- One model file per model under `models/` (exported through `models/__init__.py`).
- `BigAutoField` is the default primary key type.

## 4. Migration Policy

```bash
python manage.py makemigrations <app>
python manage.py migrate
python manage.py makemigrations --check   # CI gate — must pass clean
```

Rules:

- Never edit an applied migration that is already in production.
- New changes always create a new migration.
- Before any release, `makemigrations --check` must exit 0.

## 5. Seed Data

```bash
python manage.py seed_data
```

- Seeds core runtime settings (lookups, system settings) and example-module
  data only.
- No business-domain data is seeded outside the Example module.
- Settings are cached for 5 minutes; `set_setting()` invalidates the cache.

## 6. Backup & Restore

### SQLite (development)

```bash
python manage.py backup_db
```

### PostgreSQL (production)

```bash
# Backup
pg_dump --format=custom -f template_backup.dump "postgresql://user:pass@host:5432/db?sslmode=require"

# Restore
pg_restore --clean --if-exists -d "postgresql://user:pass@host:5432/db?sslmode=require" template_backup.dump
```

The built-in `backup_db` command supports both engines; backups are stored in
`backup/` (max `MAX_BACKUPS=10`, cooldown `BACKUP_COOLDOWN_SECONDS=60`).

### What to back up

- Database dump
- `media/` files
- `.env` (kept outside Git)

## 7. Optional Samples

The transport sample lives under `examples/transport` and remains disabled by
default. The standard migration graph contains core, accounts, and the neutral
example module only.
