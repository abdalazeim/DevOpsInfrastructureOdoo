from django import forms
from django.db import transaction

from apps.infrastructure.models import ManagedHost, ManagedService
from apps.monitoring.models import AlertRule
from apps.backup.models import BackupPolicy
from apps.automation.models import ApprovedTaskTemplate
from apps.security.models import Credential
from apps.core.services.runtime_settings import (
    RUNTIME_SETTING_SCHEMA, environment_override, get_runtime_setting,
)
from apps.core.services.system_settings import set_setting


class ManagedHostForm(forms.ModelForm):
    class Meta:
        model = ManagedHost
        fields = (
            "name", "hostname", "server_type", "connection_type", "ssh_port",
            "credential", "groups", "operating_system", "os_version",
            "architecture", "environment", "location", "ansible_limit",
            "description", "enabled", "is_local",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        is_local = cleaned.get("is_local")
        connection_type = cleaned.get("connection_type")
        server_type = cleaned.get("server_type")
        if is_local:
            cleaned["connection_type"] = ManagedHost.ConnectionType.LOCAL
            cleaned["server_type"] = ManagedHost.ServerType.LOCAL
        elif connection_type == ManagedHost.ConnectionType.LOCAL or server_type == ManagedHost.ServerType.LOCAL:
            self.add_error("is_local", "Select Local only when this Django process runs on the managed host.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Credential.objects.filter(is_active=True)
        if self.instance and self.instance.credential_id:
            queryset = Credential.objects.filter(pk=self.instance.credential_id) | queryset
        self.fields["credential"].queryset = queryset.distinct()
        self.fields["credential"].required = False
        self.fields["credential"].help_text = "Select a protected credential record. Secret material is never shown here."

    def save(self, commit=True):
        host = super().save(commit=False)
        host.credential_reference = f"credential:{host.credential_id}" if host.credential_id else ""
        if commit:
            host.save()
            self.save_m2m()
        return host


class ManagedServiceForm(forms.ModelForm):
    container_names_input = forms.CharField(
        label="Container names",
        required=False,
        help_text="Optional; enter one exact Docker container name per line.",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "odoo-container\npostgres-container"}),
    )

    class Meta:
        model = ManagedService
        fields = ("host", "key", "name", "kind", "version", "compose_project", "port", "enabled")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["host"].queryset = ManagedHost.objects.filter(enabled=True)
        if self.instance and self.instance.pk:
            self.fields["container_names_input"].initial = "\n".join(self.instance.container_names)

    def clean_container_names_input(self):
        values = [line.strip() for line in self.cleaned_data["container_names_input"].splitlines() if line.strip()]
        if len(values) > 30 or any(len(value) > 160 for value in values):
            raise forms.ValidationError("Enter up to 30 container names, each no longer than 160 characters.")
        return values

    def save(self, commit=True):
        service = super().save(commit=False)
        service.container_names = self.cleaned_data["container_names_input"]
        if commit:
            service.save()
            self.save_m2m()
        return service


class CredentialCreateForm(forms.ModelForm):
    secret = forms.CharField(
        label="Secret material", strip=False, min_length=1, max_length=20000,
        widget=forms.PasswordInput(render_value=False),
        help_text="Encrypted before storage. It is never returned by the application.",
    )

    class Meta:
        model = Credential
        fields = ("name", "kind", "username")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("kind") in {Credential.Kind.SSH_PRIVATE_KEY, Credential.Kind.SSH_PASSWORD} and not cleaned.get("username"):
            self.add_error("username", "An SSH username is required for this credential type.")
        return cleaned

    def save(self, commit=True, *, actor=None):
        credential = super().save(commit=False)
        credential.created_by = actor
        credential.set_secret(self.cleaned_data["secret"])
        if commit:
            credential.save()
        return credential


class GlobalSettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overridden = set()
        for key, spec in RUNTIME_SETTING_SCHEMA.items():
            overridden = environment_override(key) is not None
            if overridden:
                self.overridden.add(key)
            self.fields[key] = forms.IntegerField(
                label=spec["label"],
                help_text=(spec["help"] + (" This value is controlled by the environment." if overridden else "")),
                min_value=spec["minimum"], max_value=spec["maximum"],
                initial=get_runtime_setting(key), disabled=overridden,
            )

    def save(self):
        changes = []
        with transaction.atomic():
            for key, spec in RUNTIME_SETTING_SCHEMA.items():
                if key in self.overridden:
                    continue
                new_value = self.cleaned_data[key]
                old_value = get_runtime_setting(key)
                if new_value == old_value:
                    continue
                set_setting(key, new_value,
                            description=spec["help"], category=spec["category"])
                changes.append((key, old_value, new_value))
        return changes


class AlertRuleForm(forms.ModelForm):
    class Meta:
        model = AlertRule
        fields = ("name", "metric", "threshold", "cooldown_minutes", "enabled")


class BackupPolicyForm(forms.ModelForm):
    class Meta:
        model = BackupPolicy
        fields = ("name", "service", "retention_count", "schedule", "enabled")


class ApprovedTaskTemplateForm(forms.ModelForm):
    class Meta:
        model = ApprovedTaskTemplate
        fields = ("name", "description", "project_id", "template_id", "category", "read_only",
                  "requires_confirmation", "host", "service")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["host"].queryset = ManagedHost.objects.filter(enabled=True)
        self.fields["service"].queryset = ManagedService.objects.filter(enabled=True).select_related("host")
