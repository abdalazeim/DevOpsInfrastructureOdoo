"""Safe API representations and input validation for server inventory."""

from rest_framework import serializers

from apps.security.models import Credential

from .models import (
    InfrastructureSnapshot,
    InfrastructureSyncRecord,
    ManagedHost,
    ServerGroup,
    ServerTag,
)


class ServerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerGroup
        fields = ("id", "name", "description", "created_at")
        read_only_fields = ("id", "created_at")


class ServerTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerTag
        fields = ("id", "name", "color", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_color(self, value):
        if value and (
            len(value) != 7
            or value[0] != "#"
            or any(character not in "0123456789abcdefABCDEF" for character in value[1:])
        ):
            raise serializers.ValidationError("Use a six-digit hexadecimal color.")
        return value


class ManagedHostSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ServerGroup.objects.all(), required=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ServerTag.objects.all(), required=False
    )
    credential_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    has_credential = serializers.SerializerMethodField()
    latest_snapshot = serializers.SerializerMethodField()

    class Meta:
        model = ManagedHost
        fields = (
            "id", "name", "hostname", "server_type", "connection_type",
            "ssh_port", "credential_id", "has_credential", "operating_system",
            "os_version", "architecture", "location", "groups", "tags",
            "ansible_limit", "prometheus_instance", "environment",
            "description", "enabled", "is_local", "connection_status",
            "last_checked_at", "last_connection_at", "created_at", "updated_at",
            "latest_snapshot",
        )
        read_only_fields = (
            "id", "operating_system", "os_version", "architecture",
            "connection_status", "last_checked_at", "last_connection_at",
            "created_at", "updated_at", "latest_snapshot",
        )

    def get_has_credential(self, host):
        return bool(host.credential_id)

    def get_latest_snapshot(self, host):
        try:
            snapshot = host.latest_snapshot
        except InfrastructureSnapshot.DoesNotExist:
            return None
        return {
            "status": snapshot.status,
            "source": snapshot.source,
            "captured_at": snapshot.captured_at,
            "is_stale": snapshot.is_stale,
            "collection_duration_ms": snapshot.collection_duration_ms,
            "availability": snapshot.availability,
            "data": snapshot.data,
        }

    def validate(self, attrs):
        instance = self.instance
        is_local = attrs.get("is_local", getattr(instance, "is_local", False))
        server_type = attrs.get(
            "server_type", getattr(instance, "server_type", ManagedHost.ServerType.REMOTE)
        )
        connection_type = attrs.get(
            "connection_type",
            getattr(instance, "connection_type", ManagedHost.ConnectionType.SSH),
        )
        credential_id = attrs.pop("credential_id", serializers.empty)

        if is_local:
            attrs["server_type"] = ManagedHost.ServerType.LOCAL
            attrs["connection_type"] = ManagedHost.ConnectionType.LOCAL
            if credential_id not in (serializers.empty, None):
                raise serializers.ValidationError(
                    {"credential_id": "Local hosts cannot be assigned SSH credentials."}
                )
            attrs["credential"] = None
        elif (
            server_type == ManagedHost.ServerType.LOCAL
            or connection_type == ManagedHost.ConnectionType.LOCAL
        ):
            raise serializers.ValidationError(
                {"is_local": "Only the application host can use a local connection."}
            )
        elif credential_id is not serializers.empty:
            if credential_id is None:
                attrs["credential"] = None
            else:
                try:
                    credential = Credential.objects.get(pk=credential_id, is_active=True)
                except Credential.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"credential_id": "Select an active protected credential."}
                    ) from exc
                if credential.kind not in {
                    Credential.Kind.SSH_PRIVATE_KEY,
                    Credential.Kind.SSH_PASSWORD,
                }:
                    raise serializers.ValidationError(
                        {"credential_id": "The selected credential is not an SSH credential."}
                    )
                attrs["credential"] = credential

        return attrs


class InfrastructureSyncRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfrastructureSyncRecord
        fields = (
            "id", "source", "status", "updated_sections", "error_details",
            "collection_duration_ms", "started_at", "completed_at",
        )
        read_only_fields = fields
