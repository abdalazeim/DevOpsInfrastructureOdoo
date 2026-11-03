from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.security.models import Credential
from apps.security.services.credentials import CredentialEncryptionError, is_credential_encryption_ready, rotate_ciphertext


class Command(BaseCommand):
    help = "Re-encrypt stored credentials with CREDENTIAL_ENCRYPTION_KEY."

    def handle(self, *args, **options):
        if not is_credential_encryption_ready():
            raise CommandError("Configure a valid CREDENTIAL_ENCRYPTION_KEY before rotating credentials.")

        rotated = 0
        try:
            with transaction.atomic():
                for credential in Credential.objects.only("pk", "encrypted_secret").iterator(chunk_size=200):
                    credential.encrypted_secret = rotate_ciphertext(credential.encrypted_secret)
                    credential.save(update_fields=["encrypted_secret", "updated_at"])
                    rotated += 1
        except CredentialEncryptionError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Re-encrypted {rotated} credential record(s)."))
