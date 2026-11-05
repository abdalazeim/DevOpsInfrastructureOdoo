import json

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.infrastructure.models import ManagedHost, ManagedService, ServerGroup, ServerTag
from apps.monitoring.models import AlertRule
from apps.backup.models import BackupPolicy
from apps.backup.services.workflows import validate_backup_policy
from apps.automation.models import ApprovedTaskTemplate, AutomationSchedule
from apps.automation.services.execution import (
    AutomationValidationError,
    validate_variable_values,
    validate_variables_schema,
)
from apps.security.models import Credential
from apps.core.services.runtime_settings import (
    RUNTIME_SETTING_SCHEMA, environment_override, get_runtime_setting,
)
from apps.core.services.system_settings import set_setting
from apps.security.services.credentials import is_credential_encryption_ready


class ManagedHostForm(forms.ModelForm):
    class Meta:
        model = ManagedHost
        fields = (
            "name", "hostname", "server_type", "connection_type", "ssh_port",
            "credential", "groups", "tags", "operating_system", "os_version",
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


class ServerGroupForm(forms.ModelForm):
    class Meta:
        model = ServerGroup
        fields = ("name", "description")


class ServerTagForm(forms.ModelForm):
    class Meta:
        model = ServerTag
        fields = ("name", "color")

    def clean_color(self):
        color = self.cleaned_data["color"]
        if color and (
            len(color) != 7
            or color[0] != "#"
            or any(character not in "0123456789abcdefABCDEF" for character in color[1:])
        ):
            raise forms.ValidationError("Use a six-digit hexadecimal color.")
        return color


class QuickConnectServerForm(forms.Form):
    MODE_CHOICES = (
        ("ssh", "SSH server (virtual machine, VPS, or remote host)"),
        ("local", "This application host"),
    )
    connection_mode = forms.ChoiceField(
        label="Connection type", choices=MODE_CHOICES, initial="ssh",
        widget=forms.RadioSelect,
    )
    name = forms.CharField(label="Server name", max_length=120, strip=True,
                           widget=forms.TextInput(attrs={"placeholder": "Production VPS"}))
    hostname = forms.CharField(label="IP address or hostname", max_length=253, required=False, strip=True,
                               widget=forms.TextInput(attrs={"placeholder": "203.0.113.10 or server.example.com"}))
    username = forms.CharField(label="SSH login name", max_length=120, required=False, strip=True,
                               widget=forms.TextInput(attrs={"placeholder": "root or deploy", "autocomplete": "username"}))
    password = forms.CharField(
        label="Password", required=False, strip=False, max_length=20000,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )
    port = forms.IntegerField(label="SSH port", min_value=1, max_value=65535, initial=22, required=False,
                              widget=forms.NumberInput(attrs={"placeholder": "22"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("connection_mode") == "ssh":
            if not cleaned.get("hostname"):
                self.add_error("hostname", "Enter the server IP address or hostname.")
            if not cleaned.get("username"):
                self.add_error("username", "Enter the SSH login name.")
            if not cleaned.get("password"):
                self.add_error("password", "Enter the SSH password.")
            if not cleaned.get("port"):
                cleaned["port"] = 22
            if not is_credential_encryption_ready():
                self.add_error("password", "Secure credential storage is not configured on this application.")
        else:
            cleaned["hostname"] = "localhost"
            cleaned["port"] = 22
        return cleaned

    def save(self, *, actor=None):
        from django.db import transaction

        from apps.infrastructure.models import ManagedHost

        with transaction.atomic():
            credential = None
            is_local = self.cleaned_data["connection_mode"] == "local"
            if not is_local:
                credential_name = f"{self.cleaned_data['name']} SSH"[:120]
                base_name = credential_name
                suffix = 2
                while Credential.objects.filter(name=credential_name).exists():
                    tail = f" ({suffix})"
                    credential_name = f"{base_name[:120-len(tail)]}{tail}"
                    suffix += 1
                credential = Credential(
                    name=credential_name, kind=Credential.Kind.SSH_PASSWORD,
                    username=self.cleaned_data["username"], created_by=actor,
                )
                credential.set_secret(self.cleaned_data["password"])
                credential.save()
            host = ManagedHost.objects.create(
                name=self.cleaned_data["name"],
                hostname=self.cleaned_data["hostname"],
                server_type=ManagedHost.ServerType.LOCAL if is_local else ManagedHost.ServerType.REMOTE,
                connection_type=ManagedHost.ConnectionType.LOCAL if is_local else ManagedHost.ConnectionType.SSH,
                ssh_port=self.cleaned_data["port"],
                credential=credential,
                credential_reference=f"credential:{credential.pk}" if credential else "",
                is_local=is_local,
                environment=ManagedHost.Environment.PRODUCTION,
                enabled=True,
            )
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = ApprovedTaskTemplate.objects.filter(
            category=ApprovedTaskTemplate.Category.BACKUP
        ).select_related("host", "service")

    class Meta:
        model = BackupPolicy
        fields = (
            "name", "service", "template", "retention_count",
            "interval_minutes", "enabled",
        )

    def clean(self):
        cleaned = super().clean()
        for field in ("service", "template", "retention_count", "enabled"):
            if field in cleaned:
                setattr(self.instance, field, cleaned[field])
        try:
            validate_backup_policy(self.instance)
        except ValidationError as exc:
            self.add_error(None, exc)
        return cleaned


class ApprovedTaskTemplateForm(forms.ModelForm):
    variables_schema_json = forms.CharField(
        label="Allowed variables (JSON)",
        required=False,
        max_length=8192,
        help_text='Declare non-secret variables, for example {"version":{"type":"string","required":true}}.',
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "{}"}),
    )

    class Meta:
        model = ApprovedTaskTemplate
        fields = ("name", "description", "project_id", "template_id", "category", "read_only",
                  "requires_confirmation", "host", "service")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["host"].queryset = ManagedHost.objects.filter(enabled=True)
        self.fields["service"].queryset = ManagedService.objects.filter(enabled=True).select_related("host")
        if self.instance and self.instance.pk:
            self.fields["variables_schema_json"].initial = json.dumps(
                self.instance.variables_schema, ensure_ascii=True, indent=2
            )

    def clean_variables_schema_json(self):
        raw = self.cleaned_data["variables_schema_json"].strip() or "{}"
        try:
            schema = json.loads(raw)
            return validate_variables_schema(schema)
        except (json.JSONDecodeError, AutomationValidationError) as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean(self):
        cleaned = super().clean()
        host = cleaned.get("host")
        service = cleaned.get("service")
        if host and service and service.host_id != host.pk:
            self.add_error("service", "The service must belong to the selected managed host.")
        return cleaned

    def save(self, commit=True):
        template = super().save(commit=False)
        template.variables_schema = self.cleaned_data["variables_schema_json"]
        if commit:
            template.save()
            self.save_m2m()
        return template


class AutomationScheduleForm(forms.ModelForm):
    variables_json = forms.CharField(
        label="Scheduled variables (JSON)",
        required=False,
        max_length=8192,
        help_text="Values are encrypted at rest. Leave blank to keep existing values.",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "{}"}),
    )

    class Meta:
        model = AutomationSchedule
        fields = ("interval_minutes", "enabled")

    def clean_variables_json(self):
        raw = self.cleaned_data["variables_json"].strip()
        if not raw and self.instance.pk and self.instance.encrypted_variables:
            return None
        try:
            variables = json.loads(raw or "{}")
            return validate_variable_values(self.instance.template, variables)
        except (json.JSONDecodeError, AutomationValidationError) as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("enabled"):
            template = self.instance.template
            if not template.enabled:
                self.add_error("enabled", "Only approved templates can be scheduled.")
            if template.category == ApprovedTaskTemplate.Category.RESTORE:
                self.add_error("enabled", "Restore templates cannot be scheduled.")
        return cleaned
