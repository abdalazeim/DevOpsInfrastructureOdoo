from rest_framework import serializers

from apps.notifications.models import Notification, NotificationDelivery


class NotificationSerializer(serializers.ModelSerializer):
    email_status = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "category",
            "title",
            "message",
            "source_app",
            "source_model",
            "source_pk",
            "created_at",
            "read_at",
            "email_status",
        )
        read_only_fields = fields

    def get_email_status(self, notification):
        try:
            return notification.email_delivery.status
        except NotificationDelivery.DoesNotExist:
            return "not_enabled"


class NotificationPreferenceInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Notification.Category.choices)
    in_app_enabled = serializers.BooleanField(required=False)
    email_enabled = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not ({"in_app_enabled", "email_enabled"} & attrs.keys()):
            raise serializers.ValidationError(
                "At least one notification channel preference is required."
            )
        return attrs
