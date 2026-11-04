from unittest.mock import MagicMock, patch

import paramiko
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.infrastructure.models import ManagedHost
from apps.security.models import Credential
from infrastructure_engine.adapters.ssh.connection import SSHConnectionAdapter, SSHConnectionError


TEST_KEY = Fernet.generate_key().decode("ascii")


class SSHConnectionAdapterTests(TestCase):
    def create_host(self):
        credential = Credential(name="SSH ops", kind=Credential.Kind.SSH_PASSWORD, username="ops")
        credential.set_secret("never-return-this")
        credential.save()
        host = ManagedHost.objects.create(
            name="remote", hostname="remote.example.test", ssh_port=2222,
            connection_type=ManagedHost.ConnectionType.SSH, credential=credential,
        )
        return host

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    @patch("infrastructure_engine.adapters.ssh.connection.paramiko.SSHClient")
    def test_probe_uses_trusted_host_keys_fixed_command_and_returns_metadata(self, ssh_client_class):
        host = self.create_host()
        client = ssh_client_class.return_value
        stdout = MagicMock()
        client.exec_command.return_value = (MagicMock(), stdout, MagicMock())
        stdout.read.return_value = b"Linux 6.8.1 x86_64\n"
        stdout.channel.recv_exit_status.return_value = 0

        result = SSHConnectionAdapter.inspect(host)

        self.assertEqual(result, {
            "operating_system": "Linux", "os_version": "6.8.1", "architecture": "x86_64",
        })
        client.load_system_host_keys.assert_called_once_with()
        client.set_missing_host_key_policy.assert_called_once()
        self.assertIsInstance(client.set_missing_host_key_policy.call_args.args[0], paramiko.RejectPolicy)
        self.assertEqual(client.connect.call_args.kwargs["hostname"], "remote.example.test")
        self.assertEqual(client.connect.call_args.kwargs["port"], 2222)
        self.assertEqual(client.connect.call_args.kwargs["password"], "never-return-this")
        client.exec_command.assert_called_once_with("uname -srm", timeout=8)
        client.close.assert_called_once_with()

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    @patch("infrastructure_engine.adapters.ssh.connection.paramiko.SSHClient")
    def test_authentication_failure_is_redacted(self, ssh_client_class):
        host = self.create_host()
        ssh_client_class.return_value.connect.side_effect = paramiko.AuthenticationException("private auth detail")
        with self.assertRaisesRegex(SSHConnectionError, "SSH authentication failed"):
            SSHConnectionAdapter.inspect(host)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    def test_missing_credential_is_a_configuration_error_before_network_access(self):
        from infrastructure_engine.adapters.ssh.connection import SSHConnectionConfigurationError

        host = ManagedHost.objects.create(name="unconfigured", hostname="host.example.test")
        with self.assertRaises(SSHConnectionConfigurationError):
            SSHConnectionAdapter.inspect(host)
