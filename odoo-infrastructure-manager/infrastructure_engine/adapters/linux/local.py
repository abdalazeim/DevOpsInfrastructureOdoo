"""Read-only discovery of this application's Linux host using live OS metrics."""
import os
import platform
import shutil
import socket
import subprocess
import time

import psutil


def get_local_server_load():
    """Return truthful compatibility metrics for legacy orchestrator reports."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        gib = 1024 ** 3
        return {
            "cpu": f"{cpu_percent:.1f}%",
            "ram": f"{memory.used / gib:.1f}GB/{memory.total / gib:.1f}GB",
            "disk": f"{disk.percent:.1f}%",
            "source": "live-local-host",
            "available": True,
        }
    except (OSError, RuntimeError, ValueError, psutil.Error) as exc:
        return {"available": False, "source": "live-local-host", "error": type(exc).__name__}


def collect_local_snapshot():
    started = time.monotonic()
    data, availability = {}, {}
    errors = []

    def section(name, collector):
        try:
            value = collector()
        except (OSError, PermissionError, RuntimeError, ValueError, psutil.Error, subprocess.SubprocessError) as exc:
            data[name] = None
            availability[name] = {"status": "unavailable", "reason": type(exc).__name__}
            errors.append(f"{name}: {type(exc).__name__}")
            return
        data[name] = value
        if isinstance(value, dict) and value.get("supported") is False:
            availability[name] = {"status": "unsupported", "reason": value.get("reason", "Not supported on this host")}
            errors.append(f"{name}: unsupported")
        else:
            availability[name] = {"status": "available", "observed_at": time.time()}

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
    section("network_interfaces", lambda: [{"name": name, "addresses": [addr.address for addr in addresses if addr.family in (socket.AF_INET, socket.AF_INET6)]} for name, addresses in psutil.net_if_addrs().items()])
    section("dns", _dns_servers)
    section("providers", lambda: {"docker_cli": shutil.which("docker") is not None, "ansible_cli": shutil.which("ansible") is not None, "systemctl": shutil.which("systemctl") is not None})
    section("services", _running_systemd_services)
    section("processes", _top_processes)
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


def _running_systemd_services():
    executable = shutil.which("systemctl")
    if not executable:
        return {"manager": "systemd", "supported": False, "reason": "systemctl is not installed", "items": []}
    result = subprocess.run(
        [executable, "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"],
        check=True, capture_output=True, text=True, timeout=4,
        env={**os.environ, "LC_ALL": "C"}, close_fds=True,
    )
    if len(result.stdout) > 131072:
        raise ValueError("systemd service inventory exceeds the collection limit")
    items = []
    for line in result.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) >= 4:
            items.append({"unit": fields[0], "load": fields[1], "active": fields[2], "substate": fields[3], "description": fields[4] if len(fields) == 5 else ""})
    return {"manager": "systemd", "supported": True, "running_count": len(items), "items": items}


def _top_processes():
    items = []
    for process in psutil.process_iter(attrs=["pid", "name", "username", "status", "memory_percent"]):
        try:
            info = process.info
            items.append({
                "pid": info.get("pid"), "name": info.get("name") or "Unknown",
                "user": info.get("username"), "status": info.get("status"),
                "memory_percent": round(info.get("memory_percent") or 0, 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    items.sort(key=lambda item: item["memory_percent"], reverse=True)
    return {"sampled_processes": len(items), "items": items[:20], "sort": "memory_percent_desc"}
