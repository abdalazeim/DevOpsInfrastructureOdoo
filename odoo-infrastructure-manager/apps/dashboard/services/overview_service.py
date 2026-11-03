from collections import Counter

from apps.infrastructure.models import ManagedService
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
            matching = [containers_by_name.get(name) for name in service.container_names]
            matching = [item for item in matching if item]
            if not discovered["available"]:
                state = "unknown"
            elif service.container_names and len(matching) == len(service.container_names):
                state = "running" if all(item["state"] == "running" for item in matching) else "stopped"
            elif service.container_names:
                state = "unknown"
            else:
                state = "not_configured"
            services.append({"record": service, "state": state, "containers": matching})
        return {
            "containers": discovered,
            "container_counts": {
                "total": len(containers), "running": counts.get("running", 0),
                "stopped": counts.get("exited", 0) + counts.get("dead", 0),
                "unhealthy": unhealthy,
            },
            "metrics": MetricsService.collect(),
            "services": services,
            "recent_runs": [],
            "recent_alerts": [],
        }
