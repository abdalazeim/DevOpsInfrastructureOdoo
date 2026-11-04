"""Bounded Linux discovery over authenticated SSH using fixed read-only probes."""
import re
import time

from .connection import SSHConnectionAdapter

MAX_REMOTE_FILE_BYTES = 131072
MAX_COMMAND_OUTPUT_BYTES = 131072


class RemoteDiscoveryError(Exception):
    pass


def collect_ssh_snapshot(host):
    started = time.monotonic()
    client, timeout = SSHConnectionAdapter._connect_authenticated(host)
    data, availability, errors = {}, {}, []
    sftp = None

    def section(name, collector):
        try:
            value = collector()
        except Exception as exc:
            data[name] = None
            availability[name] = {"status": "unavailable", "reason": type(exc).__name__}
            errors.append(f"{name}: {type(exc).__name__}")
            return
        data[name] = value
        if isinstance(value, dict) and value.get("supported") is False:
            availability[name] = {"status": "unsupported", "reason": value.get("reason", "Not supported")}
            errors.append(f"{name}: unsupported")
        else:
            availability[name] = {"status": "available", "observed_at": time.time()}

    try:
        sftp = client.open_sftp()
        section("system", lambda: _system_info(client, sftp, timeout, host.hostname))
        section("cpu", lambda: _cpu_info(sftp))
        section("memory", lambda: _memory_info(sftp))
        section("disks", lambda: _disk_info(client, timeout))
        section("network_interfaces", lambda: _network_info(client, timeout))
        section("dns", lambda: _dns_info(sftp))
        section("services", lambda: _service_info(client, sftp, timeout))
        section("processes", lambda: _process_info(client, sftp, timeout))
        section("providers", lambda: _provider_info(sftp))
    finally:
        if sftp is not None:
            sftp.close()
        client.close()

    available = sum(item.get("status") == "available" for item in availability.values())
    status = "failed" if available == 0 else ("partial" if errors else "success")
    return {
        "source": "remote-ssh-linux", "status": status, "data": data,
        "availability": availability,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "error_details": "; ".join(errors),
    }


def _read_file(sftp, path, limit=MAX_REMOTE_FILE_BYTES):
    with sftp.open(path, "rb") as remote_file:
        raw = remote_file.read(limit + 1)
    if len(raw) > limit:
        raise RemoteDiscoveryError("Remote file exceeds the read limit")
    return raw.decode("utf-8", errors="replace")


def _run(client, command, timeout, limit=MAX_COMMAND_OUTPUT_BYTES):
    _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    channel = stdout.channel
    channel.settimeout(timeout)
    output = stdout.read(limit + 1)
    if len(output) > limit:
        channel.close()
        raise RemoteDiscoveryError("Remote command output exceeds the read limit")
    error_excerpt = stderr.read(4096)
    exit_code = channel.recv_exit_status()
    if exit_code != 0:
        raise RemoteDiscoveryError("Fixed remote read probe returned a nonzero status")
    return output.decode("utf-8", errors="replace"), error_excerpt


def _system_info(client, sftp, timeout, host_label):
    uname, _ = _run(client, "uname -srm", timeout, 1024)
    fields = uname.strip().split()
    if not fields:
        raise RemoteDiscoveryError("Remote kernel information is empty")
    release = {}
    try:
        for line in _read_file(sftp, "/etc/os-release", 8192).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                release[key] = value.strip().strip('"\'')
    except OSError:
        pass
    try:
        hostname = _read_file(sftp, "/etc/hostname", 1024).strip() or host_label
    except OSError:
        hostname = host_label
    try:
        uptime_seconds = int(float(_read_file(sftp, "/proc/uptime", 1024).split()[0]))
    except (OSError, ValueError, IndexError):
        uptime_seconds = None
    distribution = " ".join(filter(None, (release.get("NAME", ""), release.get("VERSION_ID", ""))))
    return {
        "hostname": hostname, "operating_system": fields[0],
        "distribution": distribution or fields[0],
        "kernel": fields[1] if len(fields) > 1 else "",
        "architecture": fields[2] if len(fields) > 2 else "",
        "uptime_seconds": uptime_seconds,
    }


def _cpu_info(sftp):
    cpuinfo = _read_file(sftp, "/proc/cpuinfo")
    logical_cores = sum(1 for line in cpuinfo.splitlines() if line.startswith("processor")) or None
    first = _cpu_ticks(_read_file(sftp, "/proc/stat", 4096))
    time.sleep(0.1)
    second = _cpu_ticks(_read_file(sftp, "/proc/stat", 4096))
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    usage = round(max(0.0, min(100.0, 100 * (total_delta - idle_delta) / total_delta)), 1) if total_delta > 0 else None
    try:
        load_average = [float(part) for part in _read_file(sftp, "/proc/loadavg", 1024).split()[:3]]
    except (OSError, ValueError):
        load_average = None
    return {"logical_cores": logical_cores, "physical_cores": None,
            "usage_percent": usage, "load_average": load_average}


def _cpu_ticks(stat_text):
    first = next((line for line in stat_text.splitlines() if line.startswith("cpu ")), "")
    ticks = [int(value) for value in first.split()[1:9]]
    if len(ticks) < 4:
        raise RemoteDiscoveryError("Remote CPU counters are incomplete")
    total = sum(ticks)
    idle = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)
    return total, idle


def _memory_info(sftp):
    values = {}
    for line in _read_file(sftp, "/proc/meminfo", 16384).splitlines():
        match = re.match(r"^(\w+):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    total, available = values.get("MemTotal", 0), values.get("MemAvailable", values.get("MemFree", 0))
    swap_total, swap_free = values.get("SwapTotal", 0), values.get("SwapFree", 0)
    if not total:
        raise RemoteDiscoveryError("Remote memory counters are missing")
    used = max(0, total - available)
    return {
        "total_bytes": total, "available_bytes": available, "used_bytes": used,
        "usage_percent": round(100 * used / total, 1),
        "swap_total_bytes": swap_total, "swap_used_bytes": max(0, swap_total - swap_free),
        "swap_percent": round(100 * (swap_total - swap_free) / swap_total, 1) if swap_total else 0.0,
    }


def _disk_info(client, timeout):
    output, _ = _run(client, "df -P -B1 /", timeout, 4096)
    rows = output.splitlines()
    if len(rows) < 2:
        raise RemoteDiscoveryError("Remote root filesystem was not reported")
    fields = rows[-1].split()
    if len(fields) < 6:
        raise RemoteDiscoveryError("Remote root filesystem data is invalid")
    total, used, free = (int(fields[index]) for index in (1, 2, 3))
    return [{"device": fields[0], "mountpoint": fields[-1], "filesystem": "unknown",
             "total_bytes": total, "used_bytes": used, "free_bytes": free,
             "usage_percent": round(100 * used / total, 1) if total else 0.0}]


def _network_info(client, timeout):
    output, _ = _run(client, "ip -o address show", timeout, 32768)
    interfaces = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[2] in {"inet", "inet6"}:
            name = fields[1].rstrip(":").split("@", 1)[0]
            interfaces.setdefault(name, []).append(fields[3])
    return [{"name": name, "addresses": addresses} for name, addresses in interfaces.items()]


def _dns_info(sftp):
    values = []
    for line in _read_file(sftp, "/etc/resolv.conf", 8192).splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == "nameserver":
            values.append(fields[1])
    return values


def _path_exists(sftp, paths):
    for path in paths:
        try:
            sftp.stat(path)
            return True
        except OSError:
            continue
    return False


def _service_info(client, sftp, timeout):
    if not _path_exists(sftp, ("/usr/bin/systemctl", "/bin/systemctl")):
        return {"manager": "systemd", "supported": False, "reason": "systemctl is not installed", "items": []}
    output, _ = _run(client, "systemctl list-units --type=service --state=running --no-legend --no-pager", timeout, 65536)
    items = []
    for line in output.splitlines():
        fields = line.split(None, 4)
        if len(fields) >= 4:
            items.append({"unit": fields[0], "load": fields[1], "active": fields[2],
                          "substate": fields[3], "description": fields[4] if len(fields) == 5 else ""})
    return {"manager": "systemd", "supported": True, "running_count": len(items), "items": items}


def _process_info(client, sftp, timeout):
    if not _path_exists(sftp, ("/usr/bin/ps", "/bin/ps")):
        return {"supported": False, "reason": "ps is not installed", "items": []}
    output, _ = _run(client, "ps -eo pid=,comm=,user=,state=,%mem= --sort=-%mem", timeout, 65536)
    items = []
    for line in output.splitlines():
        fields = line.split(None, 4)
        if len(fields) == 5:
            try:
                items.append({"pid": int(fields[0]), "name": fields[1], "user": fields[2],
                              "status": fields[3], "memory_percent": round(float(fields[4]), 2)})
            except ValueError:
                continue
    return {"sampled_processes": len(items), "items": items[:20], "sort": "memory_percent_desc"}


def _provider_info(sftp):
    return {
        "docker_cli": _path_exists(sftp, ("/usr/bin/docker", "/usr/local/bin/docker", "/bin/docker")),
        "ansible_cli": _path_exists(sftp, ("/usr/bin/ansible", "/usr/local/bin/ansible", "/bin/ansible")),
        "systemctl": _path_exists(sftp, ("/usr/bin/systemctl", "/bin/systemctl")),
    }
