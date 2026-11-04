import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

from django.conf import settings
from django.core.cache import cache


class MetricsService:
    """Low-cost local Linux metrics with explicit source and availability."""

    @staticmethod
    def _cpu_counters():
        values = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        numbers = [int(value) for value in values]
        idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
        return sum(numbers), idle

    @staticmethod
    def _memory():
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return None
        used = total - available
        return {"total_bytes": total, "used_bytes": used, "percent": round(used * 100 / total, 1)}

    @staticmethod
    def _network_counters():
        totals = [0, 0]
        for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
            interface, counters = line.split(":", 1)
            if interface.strip() == "lo":
                continue
            values = [int(value) for value in counters.split()]
            totals[0] += values[0]
            totals[1] += values[8]
        return totals

    @classmethod
    def collect(cls, host=None):
        if host and host.prometheus_instance and settings.PROMETHEUS_URL:
            prometheus = cls._prometheus_metrics(host.prometheus_instance)
            if prometheus["available"]:
                return prometheus
        if not host or not host.is_local:
            return {"available": False, "source": "not configured", "captured_at": None,
                    "cpu_percent": None, "memory": None, "disk": None,
                    "network_rx_bytes_per_second": None, "network_tx_bytes_per_second": None,
                    "reason": "No metrics provider is configured for this host."}
        now = time.monotonic()
        result = {"available": False, "source": "local runtime procfs", "captured_at": None,
                  "cpu_percent": None, "memory": None, "disk": None,
                  "network_rx_bytes_per_second": None, "network_tx_bytes_per_second": None}
        try:
            cpu = cls._cpu_counters()
            memory = cls._memory()
            disk_usage = shutil.disk_usage("/")
            network = cls._network_counters()
        except (OSError, ValueError, IndexError):
            result["reason"] = "Local resource metrics are not available in this runtime."
            return result

        previous = cache.get("infrastructure.metrics.previous")
        if previous:
            elapsed = now - previous["monotonic"]
            total_delta = cpu[0] - previous["cpu_total"]
            idle_delta = cpu[1] - previous["cpu_idle"]
            if elapsed > 0 and total_delta > 0:
                result["cpu_percent"] = round(max(0, min(100, (total_delta - idle_delta) * 100 / total_delta)), 1)
            if elapsed > 0:
                result["network_rx_bytes_per_second"] = round(max(0, network[0] - previous["network"][0]) / elapsed, 1)
                result["network_tx_bytes_per_second"] = round(max(0, network[1] - previous["network"][1]) / elapsed, 1)
        cache.set("infrastructure.metrics.previous", {
            "monotonic": now, "cpu_total": cpu[0], "cpu_idle": cpu[1], "network": network,
        }, timeout=300)
        result.update({
            "available": True,
            "captured_at": time.time(),
            "memory": memory,
            "disk": {"path": "/", "total_bytes": disk_usage.total,
                     "used_bytes": disk_usage.used,
                     "percent": round(disk_usage.used * 100 / disk_usage.total, 1) if disk_usage.total else None},
        })
        return result

    @staticmethod
    def _prometheus_metrics(instance):
        result = {"available": False, "source": "Prometheus / Node Exporter", "captured_at": None,
                  "cpu_percent": None, "memory": None, "disk": None,
                  "network_rx_bytes_per_second": None, "network_tx_bytes_per_second": None}
        if not instance or not all(char.isalnum() or char in "._:-" for char in instance):
            result["reason"] = "Prometheus instance label is invalid."
            return result
        base = settings.PROMETHEUS_URL.rstrip("/")
        parts = urlsplit(base)
        if not parts.hostname or (parts.scheme != "https" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}):
            result["reason"] = "Prometheus must use HTTPS unless it is local."
            return result

        def query(expression):
            url = f"{base}/api/v1/query?{urlencode({'query': expression})}"
            try:
                with urlopen(url, timeout=5) as response:
                    data = json.loads(response.read(300_000).decode("utf-8"))
                if data.get("status") != "success":
                    return None
                values = data.get("data", {}).get("result", [])
                return float(values[0]["value"][1]) if values else None
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
                return None

        label = f'instance="{instance}"'
        expressions = [
            f'100 * (1 - avg(rate(node_cpu_seconds_total{{mode="idle",{label}}}[5m])))',
            f'node_memory_MemTotal_bytes{{{label}}}',
            f'node_memory_MemAvailable_bytes{{{label}}}',
            f'node_filesystem_size_bytes{{mountpoint="/",fstype!~"tmpfs|overlay",{label}}}',
            f'node_filesystem_avail_bytes{{mountpoint="/",fstype!~"tmpfs|overlay",{label}}}',
            f'sum(rate(node_network_receive_bytes_total{{device!="lo",{label}}}[5m]))',
            f'sum(rate(node_network_transmit_bytes_total{{device!="lo",{label}}}[5m]))',
        ]
        with ThreadPoolExecutor(max_workers=4) as executor:
            values = list(executor.map(query, expressions))
        cpu, mem_total, mem_available, disk_size, disk_available, rx, tx = values
        if cpu is None and mem_total is None and disk_size is None:
            result["reason"] = "Prometheus did not return metrics for the configured instance."
            return result
        result["available"] = True
        result["captured_at"] = time.time()
        result["cpu_percent"] = round(cpu, 1) if cpu is not None else None
        if mem_total and mem_available is not None:
            used = max(0, mem_total - mem_available)
            result["memory"] = {"total_bytes": int(mem_total), "used_bytes": int(used), "percent": round(used * 100 / mem_total, 1)}
        if disk_size and disk_available is not None:
            used = max(0, disk_size - disk_available)
            result["disk"] = {"path": "/", "total_bytes": int(disk_size), "used_bytes": int(used), "percent": round(used * 100 / disk_size, 1)}
        result["network_rx_bytes_per_second"] = round(rx, 1) if rx is not None else None
        result["network_tx_bytes_per_second"] = round(tx, 1) if tx is not None else None
        return result
