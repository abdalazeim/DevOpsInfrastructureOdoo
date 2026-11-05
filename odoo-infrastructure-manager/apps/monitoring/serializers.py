from rest_framework import serializers

from apps.monitoring.models import AlertEvent, AlertRule, MetricCollection, ResourceSample


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = ("id", "name", "metric", "threshold", "cooldown_minutes", "enabled")


class ResourceSampleSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.name", read_only=True)

    class Meta:
        model = ResourceSample
        fields = (
            "id", "host", "host_name", "source", "cpu_percent",
            "memory_percent", "memory_total_bytes", "memory_used_bytes",
            "disk_percent", "network_rx_bytes_per_second",
            "network_tx_bytes_per_second", "captured_at",
        )


class AlertEventSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.name", read_only=True, default=None)
    rule_name = serializers.CharField(source="rule.name", read_only=True, default=None)
    state = serializers.SerializerMethodField()

    class Meta:
        model = AlertEvent
        fields = (
            "id", "title", "message", "host", "host_name", "rule",
            "rule_name", "state", "occurrences", "created_at", "last_seen_at",
            "acknowledged_at", "resolved_at", "notification_status",
            "last_notification_attempt_at", "notification_error",
        )

    def get_state(self, event):
        if event.resolved_at:
            return "resolved"
        if event.acknowledged_at:
            return "acknowledged"
        return "open"


class MetricCollectionSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.name", read_only=True)

    class Meta:
        model = MetricCollection
        fields = ("id", "host", "host_name", "sample", "source", "status", "error_message", "captured_at")
