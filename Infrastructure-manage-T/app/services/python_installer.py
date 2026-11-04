"""Ubuntu host installation using the operator-provided apt/PPA recipe."""
import os
import platform
import shutil
import subprocess


SUPPORTED_VERSIONS = ("3.10", "3.11", "3.12")


def build_plan(version, privileged=False):
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("Installation method supports 3.10, 3.11, and 3.12 only.")
    prefix = [] if privileged else ["sudo"]
    commands = [
        prefix + ["apt-get", "update"],
        prefix + ["apt-get", "install", "-y", "build-essential", "libssl-dev",
                  "libffi-dev", "python3-dev", "software-properties-common"],
    ]
    if version in ("3.11", "3.12"):
        commands += [
            prefix + ["add-apt-repository", "ppa:deadsnakes/ppa", "-y"],
            prefix + ["apt-get", "update"],
        ]
    commands += [
        prefix + ["apt-get", "install", "-y", f"python{version}",
                  f"python{version}-venv", f"python{version}-dev"],
        [f"/usr/bin/python{version}", "--version"],
        [f"/usr/bin/python{version}", "-c",
         f"import sys, venv, ensurepip; assert sys.version_info[:2] == {tuple(map(int, version.split('.')))!r}; print(sys.executable)"],
    ]
    return commands


def install_python(version, dry_run=False):
    privileged = hasattr(os, "geteuid") and os.geteuid() == 0
    commands = build_plan(version, privileged)
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
    # Inherit the terminal so sudo prompts and apt progress remain interactive.
    # Never kill apt on a generic workflow timeout during package installation.
    for command in commands:
        print("==>", " ".join(command), flush=True)
        try:
            result = subprocess.run(command, check=False)
        except (OSError, KeyboardInterrupt) as exc:
            print(f"Execution stopped: {exc}")
            return False
        if result.returncode:
            print(f"Command failed with code {result.returncode}. Installation stopped; see output above.")
            return False
    print(f"Python {version} installed and version check, venv, and ensurepip verified.")
    return True
