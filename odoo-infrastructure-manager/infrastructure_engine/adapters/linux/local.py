"""Read-only discovery of this application's Linux host using live OS metrics."""
import os
import platform
import shutil
import socket
import time

import psutil


def collect_local_snapshot():
    started = time.monotonic()
    data, availability = {}, {}
    errors = []

    def section(name, collector):
        try:
            value = collector()
            data[name] = value
            availability[name] = {"status": "available", "observed_at": time.time()}
        except (OSError, PermissionError, RuntimeError, ValueError) as exc:
            data[name] = None
            availability[name] = {"status": "unavailable", "reason": type(exc).__name__}
            errors.append(f"{name}: {type(exc).__name__}")

    section("system", lambda: {
        "hostname": socket.gethostname(),
        "operating_system": platform.system(),
        "distribution": " ".join(filter(None, (platform.freedesktop_os_release().get(k, "") for k in ("NAME", "VERSION_ID")))) if hasattr(platform, "freedesktop_os_release") else platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "uptime_seconds": max(0, int(time.time() - psutil.boot_time())),
    })
    section("cpu", lambda: {"logical_cores": psutil.cpu_count(), "physical_cores": psutil.cpu_count(logical=False), "usage_percent": psutil.cpu_percent(interval=0.1), "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None})
    section("memory", lambda: {"total_bytes": psutil.virtual_memory().total, "available_bytes": psutil.virtual_memory().available, "used_bytes": psutil.virtual_memory().used, "usage_percent": psutil.virtual_memory().percent, "swap_total_bytes": psutil.swap_memory().total, "swap_used_bytes": psutil.swap_memory().used, "swap_percent": psutil.swap_memory().percent})

    def disks():
        rows = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                rows.append({"device": partition.device, "mountpoint": partition.mountpoint, "filesystem": partition.fstype, "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free, "usage_percent": usage.percent})
            except (OSError, PermissionError):
                continue
        if not rows:
            raise OSError("No readable mounted filesystems")
        return rows
    section("disks", disks)
    section("network", lambda: {"interfaces": [{"name": name, "addresses": [addr.address for addr in addresses if addr.family in (socket.AF_INET, socket.AF_INET6)]} for name, addresses in psutil.net_if_addrs().items()], "dns_servers": _dns_servers()})
    section("providers", lambda: {"docker_cli": shutil.which("docker") is not None, "ansible_cli": shutil.which("ansible") is not None, "systemctl": shutil.which("systemctl") is not None})
    status = "failed" if not data else ("partial" if errors else "success")
    return {"source": "local-linux", "status": status, "data": data, "availability": availability, "duration_ms": max(0, int((time.monotonic() - started) * 1000)), "error_details": "; ".join(errors)}


def _dns_servers():
    servers = []
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as resolv:
            for line in resolv:
                fields = line.split()
                if len(fields) >= 2 and fields[0] == "nameserver":
                    servers.append(fields[1])
    except OSError:
        raise
    return servers
