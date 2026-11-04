import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from app.services.compose_installer import inspect_compose, install_compose


class TestComposeInstaller(unittest.TestCase):
    @patch('app.services.compose_installer.shutil.which', return_value=None)
    @patch('app.services.compose_installer.probe')
    def test_no_docker_does_not_execute(self, probe, which):
        self.assertEqual(inspect_compose()['status'], 'docker_missing')
        probe.assert_not_called()

    @patch('app.services.compose_installer.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.compose_installer.probe', return_value=(0, 'Docker Compose version v2.40'))
    @patch('app.services.compose_installer.run_step')
    def test_installed_plugin_not_reinstalled(self, run, probe, which):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_compose())
        run.assert_not_called()
        probe.assert_called_with(['/usr/bin/docker', 'compose', 'version'])

    @patch('app.services.compose_installer.inspect_compose', return_value={'status': 'unavailable', 'path': '/usr/bin/docker', 'details': 'error'})
    @patch('app.services.compose_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu'})
    @patch('app.services.compose_installer.run_step', side_effect=subprocess.CalledProcessError(100, ['apt-get']))
    def test_update_failure_stops_install(self, run, *_):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_compose())
        self.assertEqual(run.call_count, 1)

    @patch('app.services.compose_installer.inspect_compose', return_value={'status': 'unavailable', 'path': '/usr/bin/docker', 'details': 'error'})
    @patch('app.services.docker_installer.subprocess.run')
    def test_dry_run_has_no_mutations(self, run, inspect):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_compose(dry_run=True))
        run.assert_not_called()
