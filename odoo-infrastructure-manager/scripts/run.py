#!/usr/bin/env python
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def detect_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            out = subprocess.check_output("ipconfig", encoding="oem", errors="replace")
            for line in out.splitlines():
                m = re.search(r"IPv4[^:]*:\s*(\d+\.\d+\.\d+\.\d+)", line)
                if m and not m.group(1).startswith("127."):
                    return m.group(1)
        else:
            out = subprocess.check_output(["hostname", "-I"], encoding="utf-8")
            for ip in out.strip().split():
                if not ip.startswith("127."):
                    return ip
    except Exception:
        pass

    return "127.0.0.1"


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def find_free_port(start=8000, end=9000):
    for port in range(start, end + 1):
        if is_port_available(port):
            return port
    return None


def banner(hostname, ip, port):
    url = f"http://{ip}:{port}"
    line = "=" * 58
    print(f"""
{line}
    Django Enterprise Starter Template
{line}
    Hostname : {hostname}
    IP       : {ip}
    Port     : {port}
    URL      : {url}
{line}
    Share this URL with devices on the same network
    to access the system from phones, tablets, or PCs.
{line}
    Press Ctrl+C to stop the server.
{line}
""")


def main():
    port = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
            break

    if port is None:
        port = find_free_port(8000)
        if port is None:
            print("ERROR: No available port found in range 8000-9000.")
            sys.exit(1)

    ip = detect_ip()
    hostname = socket.gethostname()

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "config.settings.development"
    )
    os.environ.setdefault(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1," + ip
    )

    banner(hostname, ip, port)

    from django.core.management import execute_from_command_line

    sys.argv = ["manage.py", "runserver", f"0.0.0.0:{port}", "--noreload"]
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
