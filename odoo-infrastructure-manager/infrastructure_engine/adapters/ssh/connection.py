"""SSH connectivity probe using system known-host keys and fixed safe commands."""

import io
import socket

import paramiko
from apps.core.services.runtime_settings import get_runtime_setting
from apps.infrastructure.models import ManagedHost
from apps.security.models import Credential
from apps.security.services.credentials import CredentialEncryptionError


class SSHConnectionError(Exception):
    """Safe, user-displayable connection failure without credential details."""


class SSHConnectionConfigurationError(SSHConnectionError):
    """Raised when a host cannot be probed because its SSH configuration is incomplete."""


def _parse_private_key(secret):
    errors = []
    for key_class in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return key_class.from_private_key(io.StringIO(secret))
        except (paramiko.SSHException, ValueError) as exc:
            errors.append(exc)
    raise SSHConnectionError("The stored private key format is unsupported or invalid.") from errors[-1]


class SSHConnectionAdapter:
    """Performs a host-key-verified probe and reports minimal OS metadata."""

    @classmethod
    def _connect_authenticated(cls, host):
        if host.connection_type != ManagedHost.ConnectionType.SSH:
            raise SSHConnectionConfigurationError("This server is not configured for SSH.")
        if not host.credential_id:
            raise SSHConnectionConfigurationError("No protected SSH credential is assigned.")
        credential = host.credential
        if not credential.is_active:
            raise SSHConnectionConfigurationError("The assigned SSH credential is disabled.")
        if credential.kind not in {Credential.Kind.SSH_PRIVATE_KEY, Credential.Kind.SSH_PASSWORD}:
            raise SSHConnectionConfigurationError("The assigned credential is not an SSH credential.")

        try:
            secret = credential.reveal_secret()
        except CredentialEncryptionError as exc:
            raise SSHConnectionConfigurationError("The protected SSH credential could not be read.") from exc
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        timeout = get_runtime_setting("ssh_timeout_seconds")
        try:
            auth = {"password": secret, "look_for_keys": False, "allow_agent": False}
            if credential.kind == Credential.Kind.SSH_PRIVATE_KEY:
                auth.pop("password")
                auth["pkey"] = _parse_private_key(secret)
            client.connect(
                hostname=host.hostname,
                port=host.ssh_port,
                username=credential.username,
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout,
                **auth,
            )
            return client, timeout
        except paramiko.AuthenticationException as exc:
            client.close()
            raise SSHConnectionError("SSH authentication failed. Verify the credential reference.") from exc
        except paramiko.BadHostKeyException as exc:
            client.close()
            raise SSHConnectionError("The server host key did not match the trusted key.") from exc
        except SSHConnectionError:
            client.close()
            raise
        except (paramiko.SSHException, socket.timeout, TimeoutError, OSError) as exc:
            client.close()
            raise SSHConnectionError("SSH connection failed. Verify network access and trusted host keys.") from exc

    @classmethod
    def inspect(cls, host):
        client, timeout = cls._connect_authenticated(host)
        try:
            _stdin, stdout, _stderr = client.exec_command("uname -srm", timeout=timeout)
            output = stdout.read(1024).decode("utf-8", errors="replace").strip()
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0 or not output:
                raise SSHConnectionError("The remote system information probe failed.")
            parts = output.split()
            return {
                "operating_system": parts[0],
                "os_version": parts[1] if len(parts) > 1 else "",
                "architecture": parts[2] if len(parts) > 2 else "",
            }
        except (paramiko.SSHException, socket.timeout, TimeoutError, OSError) as exc:
            raise SSHConnectionError("SSH connection failed. Verify network access and trusted host keys.") from exc
        finally:
            client.close()
