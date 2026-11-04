from collections import Counter

from apps.infrastructure.models import ManagedService
from apps.automation.models import AutomationRun
from apps.monitoring.models import AlertEvent
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import ResourceSample
from .container_service import ContainerDiscoveryService
from .metrics_service import MetricsService


class DashboardOverviewService:
    @classmethod
    def build(cls):
        discovered = ContainerDiscoveryService.list_containers()
        containers = discovered["containers"]
        counts = Counter(item["state"] for item in containers)
        unhealthy = sum(item["health"] == "unhealthy" for item in containers)
        configured = list(ManagedService.objects.filter(enabled=True).select_related("host"))
        services = []
        containers_by_name = {item["name"]: item for item in containers}
        for service in configured:
            matching = [containers_by_name.get(name) for name in service.container_names] if service.host.is_local else []
            matching = [item for item in matching if item]
            if not discovered["available"]:
                state = "unknown"
            elif service.host.is_local and service.container_names and len(matching) == len(service.container_names):
                state = "running" if all(item["state"] == "running" for item in matching) else "stopped"
            elif service.container_names or not service.host.is_local:
                state = "unknown"
            else:
                state = "not_configured"
            services.append({"record": service, "state": state, "containers": matching})
        metrics_host = (ManagedHost.objects.filter(enabled=True, prometheus_instance__gt="").first()
                        or ManagedHost.objects.filter(enabled=True, is_local=True).first())
        metrics = MetricsService.collect(metrics_host) if metrics_host else MetricsService.collect()
        metrics["host_name"] = metrics_host.name if metrics_host else None
        history = []
        if metrics_host:
            history = list(ResourceSample.objects.filter(host=metrics_host).order_by("-captured_at")[:60].values(
                "captured_at", "cpu_percent", "memory_percent", "disk_percent"
            ))
            history.reverse()
        return {
            "containers": discovered,
            "container_counts": {
                "total": len(containers), "running": counts.get("running", 0),
                "stopped": max(0, len(containers) - counts.get("running", 0)),
                "unhealthy": unhealthy,
            },
            "metrics": metrics,
            "metrics_history": history,
            "services": services,
            "recent_runs": list(AutomationRun.objects.select_related("template", "requested_by")[:8]),
            "recent_alerts": list(AlertEvent.objects.select_related("rule", "host")[:6]),
        }

    @staticmethod
    def service_items(queryset):
        discovered = ContainerDiscoveryService.list_containers()
        by_name = {item["name"]: item for item in discovered["containers"]}
        items = []
        for record in queryset:
            names = getattr(record, "container_names", []) or []
            matches = [by_name[name] for name in names if name in by_name] if record.host.is_local else []
            if not discovered["available"] or not record.host.is_local or not names:
                status = "unknown"
            elif len(matches) != len(names):
                status = "not_found"
            elif all(item["state"] == "running" for item in matches):
                status = "running"
            else:
                status = "stopped"
            items.append({"record": record, "status": status, "containers": matches})
        return items
