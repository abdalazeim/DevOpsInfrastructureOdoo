"""Ubuntu host installation through the official PGDG setup script."""
import os
import platform
import shutil
import subprocess


SUPPORTED_VERSIONS = ("15", "16", "17", "18")


def build_plan(version, with_pgvector=False, privileged=False):
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("الإصدارات المتاحة: PostgreSQL 15 و16 و17 و18.")
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
        print("التثبيت المباشر متاح على Ubuntu فقط.")
        return False
    if not shutil.which("apt-get") or (not privileged and not shutil.which("sudo")):
        print("يلزم apt-get وصلاحيات root أو sudo.")
        return False
    # Keep the terminal attached for sudo and the official interactive PGDG script.
    for command in commands:
        print("==>", " ".join(command), flush=True)
        try:
            result = subprocess.run(command, check=False)
        except (OSError, KeyboardInterrupt) as exc:
            print(f"توقف التنفيذ: {exc}")
            return False
        if result.returncode:
            print(f"فشل الأمر برمز {result.returncode}. قد تكون بعض الحزم ثُبتت؛ راجع المخرجات أعلاه.")
            return False
    print(f"اكتمل تثبيت PostgreSQL {version}. راجع حالة كل cluster ومنفذه في الجدول أعلاه.")
    print("حالة خدمة postgresql العامة وحدها لا تثبت جاهزية كل قاعدة بيانات.")
    if with_pgvector:
        print("ثُبتت حزمة pgvector. بعد إنشاء قاعدة Odoo، اتصل بها ونفذ:")
        print("CREATE EXTENSION IF NOT EXISTS vector;")
        print("لم يُنفذ SQL تلقائيًا على أي قاعدة بيانات.")
    return True
