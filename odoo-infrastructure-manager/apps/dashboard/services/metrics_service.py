from pathlib import Path
import shutil
import time

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
    def collect(cls):
        now = time.monotonic()
        result = {"available": False, "source": "local Linux procfs", "captured_at": None,
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
