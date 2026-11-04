from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from apps.security.services.credentials import (
    CredentialEncryptionError,
    decrypt_secret,
    encrypt_secret,
    rotate_ciphertext,
)


class CredentialEncryptionTests(SimpleTestCase):
    def test_ciphertext_round_trip_uses_fernet(self):
        key = Fernet.generate_key().decode("ascii")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=key):
            ciphertext = encrypt_secret("private-value")
            self.assertNotIn("private-value", ciphertext)
            self.assertEqual(decrypt_secret(ciphertext), "private-value")

    def test_missing_key_fails_closed(self):
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=""):
            with self.assertRaises(CredentialEncryptionError):
                encrypt_secret("private-value")

    def test_wrong_key_cannot_decrypt_existing_ciphertext(self):
        key = Fernet.generate_key().decode("ascii")
        wrong_key = Fernet.generate_key().decode("ascii")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=key):
            ciphertext = encrypt_secret("private-value")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=wrong_key):
            with self.assertRaises(CredentialEncryptionError):
                decrypt_secret(ciphertext)

    def test_rotation_reencrypts_with_primary_before_retiring_old_key(self):
        old_key = Fernet.generate_key().decode("ascii")
        current_key = Fernet.generate_key().decode("ascii")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=old_key, CREDENTIAL_ENCRYPTION_KEY_FALLBACKS=[]):
            ciphertext = encrypt_secret("rotate-me")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=current_key,
                               CREDENTIAL_ENCRYPTION_KEY_FALLBACKS=[old_key]):
            rotated = rotate_ciphertext(ciphertext)
            self.assertEqual(decrypt_secret(rotated), "rotate-me")
        with override_settings(CREDENTIAL_ENCRYPTION_KEY=current_key, CREDENTIAL_ENCRYPTION_KEY_FALLBACKS=[]):
            self.assertEqual(decrypt_secret(rotated), "rotate-me")
