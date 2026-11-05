"""Read-only discovery of this application's Linux host using live OS metrics."""
import json
import locale
import os
import platform
import re
import selectors
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

    section("system", _system_info)
    section("cpu", _cpu_info)
    section("memory", _memory_info)
    section("storage", _disk_info)
    section("network_interfaces", _network_interfaces)
    section("network_routes", _network_routes)
    section("network_connections", _network_connections)
    section("dns", _dns_servers)
    section("providers", _provider_info)
    section("system_security", _system_security)
    section("hardware_sensors", _hardware_sensors)
    section("services", _running_systemd_services)
    section("processes", _top_processes)
    if isinstance(data.get("storage"), dict):
        data["disks"] = data["storage"]["filesystems"]
    available = sum(state["status"] == "available" for state in availability.values())
    status = "failed" if available == 0 else ("partial" if errors else "success")
    return {
        "source": "local-linux",
        "status": status,
        "data": data,
        "availability": availability,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "error_details": "; ".join(errors)[:2000],
    }


def _system_info():
    try:
        release = platform.freedesktop_os_release() if hasattr(platform, "freedesktop_os_release") else {}
    except (OSError, ValueError):
        release = {}
    version_id = release.get("VERSION_ID", "")
    distribution = release.get("NAME", "")
    try:
        timezone = _read_text_file("/etc/timezone", limit=256).strip()
    except OSError:
        timezone = ""
    locale_name = _configured_locale()
    boot_time = psutil.boot_time()
    return {
        "hostname": socket.gethostname(),
        "operating_system": platform.system(),
        "distribution": distribution or platform.platform(),
        "distribution_version": version_id or None,
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "boot_time": boot_time,
        "uptime_seconds": max(0, int(time.time() - boot_time)),
        "timezone": timezone or time.tzname[0],
        "locale": locale_name,
    }


def _configured_locale():
    try:
        for line in _read_text_file("/etc/default/locale", limit=8192).splitlines():
            match = re.match(r"^\s*(?:LANG|LC_ALL)\s*=\s*(.*?)\s*$", line)
            if match:
                return match.group(1).strip("\"'")
    except (OSError, ValueError):
        pass
    language = os.environ.get("LC_ALL") or os.environ.get("LANG")
    if language:
        return language
    current_locale = locale.getlocale()[0]
    return current_locale


def _read_text_file(path, *, limit):
    with open(path, encoding="utf-8", errors="replace") as source:
        value = source.read(limit + 1)
    if len(value) > limit:
        raise ValueError("System file exceeds the read limit")
    return value


def _cpu_info():
    model = None
    try:
        for line in _read_text_file("/proc/cpuinfo", limit=131072).splitlines():
            if line.lower().startswith(("model name", "hardware", "cpu model")) and ":" in line:
                model = line.split(":", 1)[1].strip()
                if model:
                    break
    except OSError:
        pass
    frequency = psutil.cpu_freq()
    try:
        load_average = list(os.getloadavg())
    except (AttributeError, OSError):
        load_average = None
    return {
        "model": model,
        "architecture": platform.machine(),
        "logical_cores": psutil.cpu_count(),
        "physical_cores": psutil.cpu_count(logical=False),
        "frequency_mhz": frequency.current if frequency else None,
        "usage_percent": psutil.cpu_percent(interval=0.1),
        "per_core_usage_percent": psutil.cpu_percent(interval=0.1, percpu=True),
        "load_average": load_average,
    }


def _meminfo():
    values = {}
    for line in _read_text_file("/proc/meminfo", limit=32768).splitlines():
        match = re.match(r"^(\w+):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    return values


def _memory_info():
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    try:
        values = _meminfo()
    except OSError:
        values = {}
    return {
        "total_bytes": memory.total,
        "used_bytes": memory.used,
        "available_bytes": memory.available,
        "usage_percent": memory.percent,
        "cached_bytes": values.get("Cached"),
        "buffers_bytes": values.get("Buffers"),
        "swap_total_bytes": swap.total,
        "swap_used_bytes": swap.used,
        "swap_available_bytes": max(0, swap.total - swap.used),
        "swap_percent": swap.percent,
    }


def _run_readonly(arguments, *, timeout=4, max_output=131072):
    executable = shutil.which(arguments[0])
    if not executable:
        return None
    process = subprocess.Popen(
        [executable, *arguments[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    output = bytearray()
    deadline = time.monotonic() + timeout
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(arguments, timeout)
            chunk = os.read(
                process.stdout.fileno(),
                min(65536, max_output + 1 - len(output)),
            )
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > max_output:
                process.kill()
                process.wait()
                raise ValueError("System command output exceeds the collection limit")
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, arguments)
    return output.decode("utf-8", errors="replace")


def _disk_info():
    filesystems = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (OSError, PermissionError):
            continue
        filesystems.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "filesystem": partition.fstype,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "usage_percent": usage.percent,
        })

    device_error = None
    try:
        raw_devices = _run_readonly(
            ["lsblk", "--json", "--bytes", "--output",
             "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL,ROTA"],
            max_output=262144,
        )
        document = json.loads(raw_devices) if raw_devices is not None else {}
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        raw_devices = None
        document = {}
        device_error = type(exc).__name__
    devices = []
    if raw_devices is not None:
        def append_device(item, parent=None):
            devices.append({
                "name": item.get("name"),
                "type": item.get("type"),
                "size_bytes": item.get("size"),
                "filesystem": item.get("fstype"),
                "mountpoint": item.get("mountpoint"),
                "model": item.get("model"),
                "rotational": bool(item["rota"]) if item.get("rota") is not None else None,
                "parent": parent,
            })
            for child in item.get("children") or []:
                append_device(child, item.get("name"))

        for device in document.get("blockdevices") or []:
            append_device(device)

    try:
        io = psutil.disk_io_counters(perdisk=True)
    except (OSError, psutil.Error):
        io = None
    disk_io = {
        name: {
            "read_bytes": counters.read_bytes,
            "write_bytes": counters.write_bytes,
            "read_count": counters.read_count,
            "write_count": counters.write_count,
        }
        for name, counters in (io or {}).items()
    }
    if not filesystems and raw_devices is None:
        raise OSError("No readable filesystems or block device inventory")
    return {
        "filesystems": filesystems[:128],
        "devices": devices[:128],
        "devices_truncated": len(devices) > 128,
        "devices_supported": raw_devices is not None,
        "devices_reason": device_error or ("lsblk is not installed" if raw_devices is None else ""),
        "disk_io": disk_io,
    }


def _network_interfaces():
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    counters = psutil.net_io_counters(pernic=True)
    rows = []
    for name, interface_addresses in addresses.items():
        ips = [
            address.address.split("%", 1)[0]
            for address in interface_addresses
            if address.family in (socket.AF_INET, socket.AF_INET6)
        ]
        mac = next(
            (address.address for address in interface_addresses
             if getattr(psutil, "AF_LINK", object()) == address.family),
            None,
        )
        interface_stats = stats.get(name)
        io = (counters or {}).get(name)
        rows.append({
            "name": name,
            "is_up": interface_stats.isup if interface_stats else None,
            "speed_mbps": interface_stats.speed if interface_stats and interface_stats.speed > 0 else None,
            "mtu": interface_stats.mtu if interface_stats else None,
            "addresses": ips,
            "mac_address": mac,
            "bytes_sent": io.bytes_sent if io else None,
            "bytes_received": io.bytes_recv if io else None,
            "packets_sent": io.packets_sent if io else None,
            "packets_received": io.packets_recv if io else None,
        })
    return {"items": rows[:128], "truncated": len(rows) > 128}


def _network_routes():
    output = _run_readonly(["ip", "-j", "route", "show"], max_output=65536)
    if output is None:
        return {
            "supported": False,
            "reason": "iproute2 is not installed",
            "items": [],
            "default_gateway": None,
        }
    routes = json.loads(output)
    items = [
        {
            key: route[key]
            for key in ("dst", "gateway", "dev", "protocol", "scope", "table", "metric")
            if key in route
        }
        for route in routes[:256]
    ]
    default_route = next((route for route in items if route.get("dst") == "default"), {})
    return {
        "items": items,
        "default_gateway": default_route.get("gateway"),
        "truncated": len(routes) > 256,
    }


def _address_record(address):
    if not address:
        return None
    return {"ip": address.ip, "port": address.port}


def _network_connections():
    connections = psutil.net_connections(kind="inet")
    listening = [
        connection for connection in connections
        if connection.type == socket.SOCK_STREAM and connection.status == psutil.CONN_LISTEN
    ]
    others = [
        connection for connection in connections
        if connection.type != socket.SOCK_STREAM or connection.status != psutil.CONN_LISTEN
    ]
    selected = (listening + others)[:200]
    rows = []
    for connection in selected:
        rows.append({
            "family": "ipv6" if connection.family == socket.AF_INET6 else "ipv4",
            "type": "tcp" if connection.type == socket.SOCK_STREAM else "udp",
            "local_address": _address_record(connection.laddr),
            "remote_address": _address_record(connection.raddr),
            "status": connection.status,
            "pid": connection.pid,
        })
    return {
        "items": rows,
        "listening_ports": [
            row for row in rows
            if row["type"] == "tcp" and row["status"] == psutil.CONN_LISTEN
        ],
        "truncated": len(connections) > 200,
    }


def _provider_info():
    providers = {
        "package_managers": {
            "apt": shutil.which("apt-get") is not None,
            "dpkg": shutil.which("dpkg") is not None,
        },
        "ansible": {"installed": shutil.which("ansible") is not None},
        "docker": {"installed": shutil.which("docker") is not None},
        "systemd": {"installed": shutil.which("systemctl") is not None},
        "smartctl": {"installed": shutil.which("smartctl") is not None},
    }
    if providers["docker"]["installed"]:
        try:
            output = _run_readonly(
                ["docker", "info", "--format", "{{json .}}"],
                timeout=3,
                max_output=65536,
            )
            info = json.loads(output) if output else {}
            providers["docker"].update({
                "engine_status": "available" if info else "unavailable",
                "engine_version": info.get("ServerVersion"),
                "api_version": info.get("APIVersion"),
                "storage_driver": info.get("Driver"),
                "operating_system": info.get("OperatingSystem"),
                "architecture": info.get("Architecture"),
                "cpu_count": info.get("NCPU"),
                "memory_bytes": info.get("MemTotal"),
                "root_directory": info.get("DockerRootDir"),
            })
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            providers["docker"].update({
                "engine_status": "unavailable",
                "reason": type(exc).__name__,
            })
    else:
        providers["docker"]["engine_status"] = "not_installed"
    return providers


def _system_security():
    ufw_path = shutil.which("ufw")
    ufw = {"installed": bool(ufw_path), "status": "unknown"}
    if ufw_path:
        try:
            output = _run_readonly(["ufw", "status"], timeout=3, max_output=4096)
            status_line = next(
                (line.strip() for line in output.splitlines() if line.strip().lower().startswith("status:")),
                None,
            )
            ufw["status"] = status_line.split(":", 1)[1].strip().lower() if status_line else "unknown"
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            ufw["reason"] = type(exc).__name__
    return {
        "effective_uid": os.geteuid() if hasattr(os, "geteuid") else None,
        "running_as_root": bool(hasattr(os, "geteuid") and os.geteuid() == 0),
        "ufw": ufw,
    }


def _hardware_sensors():
    temperature_reader = getattr(psutil, "sensors_temperatures", None)
    battery_reader = getattr(psutil, "sensors_battery", None)
    if not temperature_reader and not battery_reader:
        return {"supported": False, "reason": "Hardware sensors are not supported on this platform"}

    temperatures = {}
    temperature_supported = bool(temperature_reader)
    if temperature_reader:
        try:
            raw = temperature_reader(fahrenheit=False) or {}
            temperatures = {
                name: [
                    {
                        "label": item.label or name,
                        "current_celsius": item.current,
                        "high_celsius": item.high,
                        "critical_celsius": item.critical,
                    }
                    for item in sensors[:32]
                ]
                for name, sensors in list(raw.items())[:32]
            }
        except NotImplementedError:
            temperature_supported = False
    battery = None
    battery_supported = bool(battery_reader)
    if battery_reader:
        try:
            value = battery_reader()
            if value:
                battery = {
                    "percent": value.percent,
                    "plugged": value.power_plugged,
                    "seconds_left": value.secsleft,
                }
        except NotImplementedError:
            battery_supported = False
    if not temperatures and battery is None:
        return {
            "supported": False,
            "reason": "No hardware sensors are exposed to this process",
            "temperatures": {},
            "battery": None,
            "temperature_supported": temperature_supported,
            "battery_supported": battery_supported,
        }
    return {
        "temperatures": temperatures,
        "battery": battery,
        "temperature_supported": temperature_supported,
        "battery_supported": battery_supported,
    }


def _dns_servers():
    servers = []
    for line in _read_text_file("/etc/resolv.conf", limit=32768).splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == "nameserver":
            servers.append(fields[1])
    return servers[:64]


def _running_systemd_services():
    if not shutil.which("systemctl"):
        return {"manager": "systemd", "supported": False, "reason": "systemctl is not installed", "items": []}
    output = _run_readonly(
        ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"],
        timeout=4,
        max_output=131072,
    )
    items = []
    for line in (output or "").splitlines():
        fields = line.split(None, 4)
        if len(fields) >= 4:
            items.append({"unit": fields[0], "load": fields[1], "active": fields[2], "substate": fields[3], "description": fields[4] if len(fields) == 5 else ""})
    return {
        "manager": "systemd",
        "supported": True,
        "running_count": len(items),
        "items": items[:500],
        "truncated": len(items) > 500,
    }


def _top_processes():
    items = []
    processes = iter(psutil.process_iter(
        attrs=["pid", "name", "username", "status", "memory_percent"]
    ))
    sampled = 0
    truncated = False
    for process in processes:
        if sampled >= 2000:
            truncated = True
            break
        sampled += 1
        try:
            info = process.info
            memory_percent = info.get("memory_percent")
            items.append({
                "pid": info.get("pid"), "name": info.get("name") or "Unknown",
                "user": info.get("username"), "status": info.get("status"),
                "memory_percent": round(memory_percent, 2) if memory_percent is not None else None,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    items.sort(
        key=lambda item: item["memory_percent"] if item["memory_percent"] is not None else -1,
        reverse=True,
    )
    return {
        "sampled_processes": sampled,
        "items": items[:20],
        "truncated": truncated,
        "sort": "memory_percent_desc",
    }
