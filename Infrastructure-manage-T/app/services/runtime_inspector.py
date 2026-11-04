"""Read-only discovery of host runtimes and local Docker resources."""
import glob
import json
import shutil
import subprocess
import sys


VERSIONS = {"python": ("3.10", "3.11", "3.12"), "postgresql": ("15", "16", "17", "18")}


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, str(exc)


def inspect_host(component):
    if component not in VERSIONS:
        raise ValueError("Unknown component")
    if component == "python":
        candidates = [sys.executable]
        candidates += [shutil.which(name) for name in ("python", "python3", *(f"python{v}" for v in VERSIONS[component]))]
        candidates += glob.glob("/usr/bin/python3.*") + glob.glob("/usr/local/bin/python3.*")
    else:
        candidates = [shutil.which("postgres")]
        candidates += glob.glob("/usr/lib/postgresql/*/bin/postgres")
        candidates += glob.glob("C:/Program Files/PostgreSQL/*/bin/postgres.exe")
    records = []
    errors = []
    for path in dict.fromkeys(p for p in candidates if p):
        code, output = probe([path, "--version"])
        if code == 0:
            records.append({"path": path, "version": output})
        else:
            errors.append(f"{path}: {output}")
    # psql alone is a client, not evidence that a database server is installed.
    details = ""
    if component == "postgresql" and shutil.which("pg_lsclusters"):
        code, details = probe(["pg_lsclusters"])
        if code != 0:
            errors.append(details)
            details = ""
    return {"records": records, "details": details, "errors": errors}


def inspect_docker(component):
    if component not in VERSIONS:
        raise ValueError("Unknown component")
    if not shutil.which("docker"):
        return {"records": [], "errors": ["Docker غير مثبت أو غير موجود في PATH."]}
    repository = "python" if component == "python" else "postgres"
    records, errors = [], []
    for kind, command in (
        ("container", ["docker", "ps", "-a", "--format", "{{json .}}"]),
        ("image", ["docker", "image", "ls", "--format", "{{json .}}"]),
    ):
        code, output = probe(command)
        if code != 0:
            errors.append(output)
            continue
        for line in output.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                errors.append("تعذر قراءة نتيجة Docker.")
                continue
            image = item.get("Image", item.get("Repository", ""))
            name = image.split("/")[-1].split(":")[0].split("@")[0]
            if name == repository:
                records.append({"kind": kind, "image": image, "tag": item.get("Tag", ""),
                                "name": item.get("Names", ""), "status": item.get("Status", "")})
    return {"records": records, "errors": errors}
