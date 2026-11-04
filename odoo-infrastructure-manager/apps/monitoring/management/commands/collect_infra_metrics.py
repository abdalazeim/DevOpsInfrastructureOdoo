from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from apps.dashboard.services.metrics_service import MetricsService
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import AlertEvent, AlertRule, ResourceSample


class Command(BaseCommand):
    help = "Collect one sample from configured local or Prometheus providers and evaluate enabled alert rules."

    def handle(self, *args, **options):
        hosts = ManagedHost.objects.filter(enabled=True).filter(Q(is_local=True) | ~Q(prometheus_instance=""))
        if not hosts.exists():
            raise CommandError("No enabled host has a configured local or Prometheus metrics provider.")
        created = 0
        saved = 0
        for host in hosts:
            data = MetricsService.collect(host)
            if not data.get("available"):
                self.stderr.write(f"Skipped {host.name}: {data.get('reason', 'metrics unavailable')}")
                continue
            memory = data.get("memory") or {}
            disk = data.get("disk") or {}
            sample = ResourceSample.objects.create(
                host=host, source=data.get("source", "unknown"),
                cpu_percent=data.get("cpu_percent"),
                memory_percent=memory.get("percent"),
                memory_total_bytes=memory.get("total_bytes"),
                memory_used_bytes=memory.get("used_bytes"),
                disk_percent=disk.get("percent"),
                network_rx_bytes_per_second=data.get("network_rx_bytes_per_second"),
                network_tx_bytes_per_second=data.get("network_tx_bytes_per_second"),
            )
            saved += 1
            created += self._evaluate(host, sample)
            ResourceSample.objects.filter(host=host, captured_at__lt=timezone.now() - timedelta(days=30)).delete()
        self.stdout.write(self.style.SUCCESS(f"Saved {saved} resource sample(s); created {created} alert(s)."))

    @staticmethod
    def _evaluate(host, sample):
        values = {
            "cpu_percent": sample.cpu_percent,
            "memory_percent": sample.memory_percent,
            "disk_percent": sample.disk_percent,
        }
        created = 0
        for rule in AlertRule.objects.filter(enabled=True):
            value = values.get(rule.metric)
            if value is None or value < rule.threshold:
                continue
            cutoff = timezone.now() - timedelta(minutes=rule.cooldown_minutes)
            if AlertEvent.objects.filter(rule=rule, host=host, created_at__gte=cutoff).exists():
                continue
            event = AlertEvent.objects.create(
                rule=rule, host=host,
                title=f"{rule.get_metric_display()} threshold exceeded",
                message=f"{rule.get_metric_display()} is {value:.1f}% (threshold {rule.threshold:.1f}%).",
            )
            created += 1
            from django.conf import settings
            if getattr(settings, "DEFAULT_FROM_EMAIL", "") and getattr(settings, "EMAIL_HOST", ""):
                try:
                    send_mail(event.title, event.message, settings.DEFAULT_FROM_EMAIL,
                              settings.INFRA_ALERT_EMAILS, fail_silently=True)
                except Exception:
                    pass
        return created
