import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from app.services.docker_installer import installed_conflicts, repository_plan, package_command, install_docker


class TestDockerInstaller(unittest.TestCase):
    @patch('app.services.docker_installer.subprocess.run', return_value=SimpleNamespace(
        stdout='docker.io\tinstall\ncontainerd\thold\nrunc\tdeinstall\nother\tinstall\n'))
    def test_conflicts_only_installed_packages(self, run):
        self.assertEqual(installed_conflicts(), ['docker.io', 'containerd'])

    def test_repository_content_and_no_empty_removal(self):
        steps = repository_plan('jammy', 'arm64')
        self.assertFalse(any('remove' in c for c, _ in steps))
        content = next(content for _, content in steps if content)
        self.assertIn('Suites: jammy\n', content)
        self.assertIn('Architectures: arm64\n', content)

    def test_removal_keeps_apt_confirmation(self):
        command = repository_plan('noble', 'amd64', ['docker.io'])[0][0]
        self.assertIn('remove', command)
        self.assertNotIn('-y', command)
        self.assertNotIn('purge', command)

    def test_version_pins_both_packages(self):
        command = package_command('5:28.0.0-1~ubuntu.24.04~noble')
        self.assertIn('docker-ce=5:28.0.0-1~ubuntu.24.04~noble', command)
        self.assertIn('docker-ce-cli=5:28.0.0-1~ubuntu.24.04~noble', command)

    def test_reject_invalid_values(self):
        with self.assertRaises(ValueError):
            repository_plan('noble;bad', 'amd64')
        with self.assertRaises(ValueError):
            package_command('--bad')

    @patch('app.services.docker_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_CODENAME': 'noble'})
    @patch('app.services.docker_installer.subprocess.run', side_effect=[SimpleNamespace(stdout='amd64\n'), SimpleNamespace(stdout='')])
    def test_dry_run_only_queries_dpkg(self, run, release):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_docker(dry_run=True, hello_world=True, group_user='operator'))
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(call.args[0][0] == 'dpkg' for call in run.call_args_list))

    @patch('builtins.input', return_value='y')
    @patch('app.services.docker_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_CODENAME': 'noble'})
    @patch('app.services.docker_installer.subprocess.run')
    def test_first_mutation_failure_stops(self, run, *_):
        import subprocess
        run.side_effect = [SimpleNamespace(stdout='amd64'), SimpleNamespace(stdout=''), subprocess.CalledProcessError(100, ['apt-get'])]
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_docker())
        self.assertEqual(run.call_count, 3)

    @patch('builtins.input', return_value='y')
    @patch('app.services.docker_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_CODENAME': 'noble'})
    @patch('app.services.docker_installer.subprocess.run')
    def test_success_verifies_local_engine_and_optional_actions(self, run, *_):
        run.side_effect = [SimpleNamespace(stdout='amd64'), SimpleNamespace(stdout='')] + [SimpleNamespace(returncode=0)] * 20
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_docker(hello_world=True, group_user='operator'))
        commands = [call.args[0] for call in run.call_args_list]
        docker_commands = [c for c in commands if 'docker' in c and '--host' in c]
        self.assertEqual(len(docker_commands), 4)
        self.assertTrue(all('unix:///var/run/docker.sock' in c for c in docker_commands))
        self.assertTrue(any(c[-3:] == ['-aG', 'docker', 'operator'] for c in commands))
