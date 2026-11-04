"""Ubuntu host installation through the official PGDG setup script."""
import os
import platform
import shutil
import subprocess


SUPPORTED_VERSIONS = ("15", "16", "17", "18")


def build_plan(version, with_pgvector=False, privileged=False):
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("Available versions: PostgreSQL 15, 16, 17, 18.")
    prefix = [] if privileged else ["sudo"]
    commands = [
        prefix + ["apt-get", "update"],
        prefix + ["apt-get", "install", "-y", "postgresql-common"],
        prefix + ["/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh"],
        prefix + ["apt-get", "update"],
        prefix + ["apt-get", "install", "-y", f"postgresql-{version}",
                  f"postgresql-client-{version}", "libpq-dev"],
    ]
    if with_pgvector:
        commands.append(prefix + ["apt-get", "install", "-y", f"postgresql-{version}-pgvector"])
    commands += [
        [f"/usr/lib/postgresql/{version}/bin/postgres", "--version"],
        ["pg_lsclusters"],
        ["systemctl", "--no-pager", "--full", "status", "postgresql"],
    ]
    return commands


def install_postgresql(version, with_pgvector=False, dry_run=False):
    privileged = hasattr(os, "geteuid") and os.geteuid() == 0
    commands = build_plan(version, with_pgvector, privileged)
    if dry_run:
        for command in commands:
            print("[DRY-RUN]", " ".join(command))
        return True
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        release = {}
    if release.get("ID") != "ubuntu":
        print("Direct installation is available on Ubuntu only.")
        return False
    if not shutil.which("apt-get") or (not privileged and not shutil.which("sudo")):
        print("apt-get and root or sudo privileges are required.")
        return False
    # Keep the terminal attached for sudo and the official interactive PGDG script.
    for command in commands:
        print("==>", " ".join(command), flush=True)
        try:
            result = subprocess.run(command, check=False)
        except (OSError, KeyboardInterrupt) as exc:
            print(f"Execution stopped: {exc}")
            return False
        if result.returncode:
            print(f"Command failed with code {result.returncode}. Some packages may have been installed; see output above.")
            return False
    print(f"PostgreSQL {version} installation completed. Check each cluster status and port in the table above.")
    print("postgresql service status alone does not prove every database is ready.")
    if with_pgvector:
        print("pgvector package installed. After creating the Odoo database, connect to it and run:")
        print("CREATE EXTENSION IF NOT EXISTS vector;")
        print("No SQL was executed automatically on any database.")
    return True
