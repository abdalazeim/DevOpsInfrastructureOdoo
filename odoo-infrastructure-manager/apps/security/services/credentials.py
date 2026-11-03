"""Authenticated encryption helpers for persisted credentials."""

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class CredentialEncryptionError(Exception):
    """Raised when the credential encryption key is missing or invalid."""


def _fernet():
    key = getattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "")
    if not key:
        raise CredentialEncryptionError("CREDENTIAL_ENCRYPTION_KEY is not configured.")
    try:
        primary = Fernet(key.encode("ascii"))
        fallbacks = [Fernet(item.encode("ascii")) for item in getattr(settings, "CREDENTIAL_ENCRYPTION_KEY_FALLBACKS", [])]
        return MultiFernet([primary, *fallbacks])
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError("CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def encrypt_secret(raw_secret):
    if not isinstance(raw_secret, str) or not raw_secret:
        raise CredentialEncryptionError("A non-empty secret is required.")
    return _fernet().encrypt(raw_secret.encode("utf-8")).decode("ascii")


def is_credential_encryption_ready():
    try:
        _fernet()
    except CredentialEncryptionError:
        return False
    return True


def decrypt_secret(ciphertext):
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialEncryptionError("Credential decryption failed; verify the active encryption key.") from exc


def rotate_ciphertext(ciphertext):
    """Re-encrypt a stored value with the primary key while accepting fallback keys."""
    try:
        return _fernet().rotate(ciphertext.encode("ascii")).decode("ascii")
    except InvalidToken as exc:
        raise CredentialEncryptionError("Credential cannot be decrypted by the configured key ring.") from exc
