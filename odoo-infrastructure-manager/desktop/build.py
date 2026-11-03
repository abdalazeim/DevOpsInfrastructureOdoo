import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DESKTOP_DIR = Path(__file__).resolve().parent
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
APP_NAME = "Django Enterprise Starter"
OUTPUT_FOLDER = DIST_DIR / APP_NAME
SPEC_FILE = PROJECT_DIR / f"{APP_NAME}.spec"
ICON_FILE = BUILD_DIR / "icon.ico"


def clean_build_artifacts():
    print("[CLEAN] Removing build artifacts...")
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Removed: {d}")
    if SPEC_FILE.exists():
        SPEC_FILE.unlink()
        print(f"  Removed: {SPEC_FILE}")
    print("[CLEAN] Done.\n")


def install_dependencies():
    print("[DEPS] Installing build dependencies...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "pyinstaller",
            "waitress",
            "openpyxl",
            "pillow",
            "pystray",
        ]
    )
    print("[DEPS] Done.\n")


def collect_static():
    print("[STATIC] Collecting static files...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desktop")
    try:
        import django

        django.setup()
        from django.core.management import call_command

        call_command("collectstatic", "--noinput", verbosity=1)
    except Exception as e:
        print(f"  Warning: collectstatic failed: {e}")
    print("[STATIC] Done.\n")


def build():
    print("[BUILD] Building application...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=" + APP_NAME,
        "--onedir",
        "--windowed",
        "--add-data",
        f"config{os.pathsep}config",
        "--add-data",
        f"apps{os.pathsep}apps",
        "--hidden-import=django",
        "--hidden-import=django.contrib.admin",
        "--hidden-import=django.contrib.auth",
        "--hidden-import=django.contrib.contenttypes",
        "--hidden-import=django.contrib.sessions",
        "--hidden-import=django.contrib.messages",
        "--hidden-import=django.contrib.staticfiles",
        "--hidden-import=django.contrib.admin.templatetags",
        "--hidden-import=config",
        "--hidden-import=config.settings",
        "--hidden-import=config.settings.desktop",
        "--hidden-import=config.urls",
        "--hidden-import=config.wsgi",
        "--hidden-import=apps",
        "--hidden-import=apps.core",
        "--hidden-import=apps.accounts",
        "--hidden-import=apps.modules.example",
        "--hidden-import=tkinter",
        "--hidden-import=waitress",
        "--hidden-import=waitress.server",
        "--hidden-import=waitress.adjustments",
        "--hidden-import=openpyxl",
        "--hidden-import=psycopg2",
        "--hidden-import=psycopg2.extensions",
        "--hidden-import=psycopg2.extras",
        "--hidden-import=dj_database_url",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--collect-all=django",
        "--noconfirm",
    ]
    if ICON_FILE.exists():
        cmd.append("--icon=" + str(ICON_FILE))
    cmd.append(str(DESKTOP_DIR / "desktop_launcher.py"))
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode == 0:
        print("[BUILD] Build successful!\n")
    else:
        print(f"[BUILD] Build failed with code {result.returncode}\n")
    return result.returncode


def post_build():
    print("[POST-BUILD] Setting up distribution folder...")

    staticfiles_source = PROJECT_DIR / "staticfiles"
    media_source = PROJECT_DIR / "media"
    backup_source = PROJECT_DIR / "backup"

    if not (OUTPUT_FOLDER / f"{APP_NAME}.exe").exists():
        print(f"  PyInstaller output not found at: {OUTPUT_FOLDER}")
        return

    (OUTPUT_FOLDER / "staticfiles").mkdir(parents=True, exist_ok=True)
    if staticfiles_source.exists():
        for item in staticfiles_source.iterdir():
            dest = OUTPUT_FOLDER / "staticfiles" / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"  Copied staticfiles to: {OUTPUT_FOLDER / 'staticfiles'}")

    (OUTPUT_FOLDER / "media").mkdir(parents=True, exist_ok=True)
    if media_source.exists():
        for item in media_source.iterdir():
            dest = OUTPUT_FOLDER / "media" / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"  Copied media to: {OUTPUT_FOLDER / 'media'}")

    (OUTPUT_FOLDER / "backup").mkdir(parents=True, exist_ok=True)
    if backup_source.exists():
        for item in backup_source.iterdir():
            dest = OUTPUT_FOLDER / "backup" / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"  Copied backup to: {OUTPUT_FOLDER / 'backup'}")

    readme_path = OUTPUT_FOLDER / "README.txt"
    readme_path.write_text(
        "Django Enterprise Starter Template\n"
        "====================================\n\n"
        "To run: Double-click on:\n"
        f"  {APP_NAME}.exe\n\n"
        "Create the first administrator before startup by setting these\n"
        "environment variables in the launching shell:\n"
        "  DJANGO_SEED_ADMIN=True\n"
        "  DJANGO_ADMIN_USERNAME=<your username>\n"
        "  DJANGO_ADMIN_PASSWORD=<a strong unique password>\n"
        "After the first startup, remove DJANGO_SEED_ADMIN from the shell.\n\n"
        "Data is stored locally in db.sqlite3 (no PostgreSQL required).\n\n"
        "If port 8000 is busy, the app will try ports 8001-8020.\n"
    )
    print("  Created README.txt")

    print("[POST-BUILD] Done.\n")


def main():
    clean_mode = "--clean" in sys.argv

    print("=" * 60)
    print(f"  {APP_NAME} - Desktop Build Tool")
    print("=" * 60)
    print()

    if clean_mode:
        clean_build_artifacts()

    install_dependencies()
    collect_static()
    build()
    post_build()

    exe_path = OUTPUT_FOLDER / f"{APP_NAME}.exe"
    if exe_path.exists():
        print("=" * 60)
        print("  BUILD COMPLETE!")
        print("=" * 60)
        print(f"  Folder: {OUTPUT_FOLDER}")
        print(f"  Executable: {exe_path}")
        print()
        print("  Folder contents:")
        for item in sorted(OUTPUT_FOLDER.iterdir()):
            if item.name == "_internal":
                print(
                    f"    - {item.name}/ ({sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB)"
                )
            else:
                print(f"    - {item.name}")
        print()
        print("  To distribute: Copy the entire folder to any Windows PC")
        print(f"  and run {APP_NAME}.exe")
        print("=" * 60)
    else:
        print("BUILD FAILED. Check the output above for errors.")


if __name__ == "__main__":
    main()
