"""Backup engine: pg_dump/pg_restore with a portable dumpdata fallback.

Kept separate from views so management commands and future tooling reuse it.
"""
import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings


def get_backup_dir():
    backup_dir = getattr(settings, "BACKUP_DIR", Path(settings.BASE_DIR) / "backup")
    return Path(backup_dir)


def get_db_config():
    return settings.DATABASES["default"]


def validate_filename(filename):
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return False
    if not (filename.endswith(".dump") or filename.endswith(".json")):
        return False
    return True


def _pg_binary(name):
    """Return full path to a PostgreSQL client binary, or '' if unavailable."""
    exe = name + ".exe"
    for path in [
        r"C:\Program Files\PostgreSQL\16\bin",
        r"C:\Program Files\PostgreSQL\15\bin",
        r"C:\Program Files\PostgreSQL\14\bin",
        r"C:\Program Files\PostgreSQL\13\bin",
    ]:
        if Path(path).joinpath(exe).exists():
            return str(Path(path) / exe)
    which = shutil.which(name)
    if which:
        return which
    return ""


def pg_tools_available():
    return bool(_pg_binary("pg_dump"))


def _dumpdata_json(dest):
    """Portable full-DB backup using Django's serializer (no pg_dump needed)."""
    from django.apps import apps
    from django.core import serializers

    models = [
        model
        for model in apps.get_models()
        if not model._meta.proxy and model._meta.managed
    ]
    objects = []
    for model in models:
        try:
            objects.extend(model.objects.all())
        except Exception:
            continue
    data = serializers.serialize(
        "json", objects, indent=2, use_natural_foreign_keys=True
    )
    with open(dest, "w", encoding="utf-8") as f:
        f.write(data)


def _loaddata_json(src):
    """Portable full-DB restore: clear existing rows then load the fixture."""
    from django.core.management import call_command

    call_command("flush", interactive=False, verbosity=0)
    call_command("loaddata", str(src), verbosity=0)


def _pg_dump(dest):
    config = get_db_config()
    host = config.get("HOST", "localhost")
    port = config.get("PORT", "5432")
    name = config["NAME"]
    user = config["USER"]
    pg_dump = _pg_binary("pg_dump")
    env = os.environ.copy()
    if config.get("PASSWORD"):
        env["PGPASSWORD"] = config["PASSWORD"]
    result = subprocess.run(
        [
            pg_dump,
            "--host",
            host,
            "--port",
            str(port),
            "--username",
            user,
            "--format",
            "c",
            "--file",
            str(dest),
            name,
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")


def do_backup(dest):
    """Create a backup.

    Uses pg_dump when available; otherwise (or on pg_dump failure such as a
    server/client version mismatch) falls back to a portable dumpdata JSON.
    Returns the filename actually written (extension may change to .json).
    """
    if pg_tools_available():
        try:
            _pg_dump(dest)
            return dest.name
        except RuntimeError:
            pass
    dest = dest.with_suffix(".json")
    _dumpdata_json(dest)
    return dest.name


def do_restore(src):
    if src.suffix == ".json" or not pg_tools_available():
        _loaddata_json(src)
        return

    config = get_db_config()
    host = config.get("HOST", "localhost")
    port = config.get("PORT", "5432")
    name = config["NAME"]
    user = config["USER"]
    pg_restore = _pg_binary("pg_restore")
    env = os.environ.copy()
    if config.get("PASSWORD"):
        env["PGPASSWORD"] = config["PASSWORD"]
    result = subprocess.run(
        [
            pg_restore,
            "--host",
            host,
            "--port",
            str(port),
            "--username",
            user,
            "--dbname",
            name,
            "--clean",
            "--if-exists",
            str(src),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_restore failed: {result.stderr}")


def format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
