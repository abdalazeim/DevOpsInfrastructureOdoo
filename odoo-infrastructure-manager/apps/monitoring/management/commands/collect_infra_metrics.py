from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.core.services.runtime_settings import get_runtime_setting
from apps.infrastructure.models import ManagedHost
from apps.monitoring.services.collection import collect_host, prune_metrics


class Command(BaseCommand):
    help = "Collect configured infrastructure metrics, evaluate alerts, and prune expired data."

    def handle(self, *args, **options):
        interval = get_runtime_setting("monitoring_collection_interval_seconds")
        retention = get_runtime_setting("metrics_retention_days")
        hosts = ManagedHost.objects.filter(enabled=True).filter(
            Q(is_local=True) | ~Q(prometheus_instance="")
        ).order_by("pk")
        if not hosts.exists():
            prune_metrics(retention)
            raise CommandError(
                "No enabled host has a configured local or Prometheus metrics provider."
            )

        collected = skipped = failed = alerts = 0
        for host in hosts.iterator():
            result = collect_host(host, interval)
            if result.status == "success":
                collected += 1
                alerts += result.alerts_created
                self.stdout.write(f"Collected {host.name} from {result.source}.")
            elif result.status == "skipped":
                skipped += 1
                self.stdout.write(f"Skipped {host.name}: {result.reason}")
            else:
                failed += 1
                self.stderr.write(f"Collection failed for {host.name}: {result.reason}")

        deleted_samples, deleted_collections = prune_metrics(retention)
        self.stdout.write(
            self.style.SUCCESS(
                f"Collected {collected}; skipped {skipped}; failed {failed}; "
                f"created {alerts} alert(s); pruned {deleted_samples} sample(s) and "
                f"{deleted_collections} collection record(s)."
            )
        )
        if failed:
            raise CommandError(f"Collection failures: {failed}.")
