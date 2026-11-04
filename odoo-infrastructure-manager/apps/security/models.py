from django.conf import settings
from django.db import models


class Credential(models.Model):
    class Kind(models.TextChoices):
        SSH_PRIVATE_KEY = "ssh_private_key", "SSH private key"
        SSH_PASSWORD = "ssh_password", "SSH password"
        API_TOKEN = "api_token", "API token"

    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    username = models.CharField(max_length=120, blank=True)
    encrypted_secret = models.TextField()
    fingerprint = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="created_credentials")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    def set_secret(self, raw_secret):
        from .services.credentials import encrypt_secret

        self.encrypted_secret = encrypt_secret(raw_secret)

    def reveal_secret(self):
        from .services.credentials import decrypt_secret

        return decrypt_secret(self.encrypted_secret)
