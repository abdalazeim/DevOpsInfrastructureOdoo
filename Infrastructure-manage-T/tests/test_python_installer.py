import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from app.services.python_installer import build_plan, install_python


class TestPythonInstaller(unittest.TestCase):
    def test_user_recipe_versions(self):
        for version in ('3.10', '3.11', '3.12'):
            commands = build_plan(version)
            self.assertEqual(any('ppa:deadsnakes/ppa' in c for c in commands), version != '3.10')
            self.assertTrue(any(f'python{version}-venv' in c and f'python{version}-dev' in c for c in commands))
            self.assertFalse(any('update-alternatives' in c for c in commands))

    @patch('app.services.python_installer.subprocess.run')
    def test_dry_run_never_executes(self, run):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_python('3.12', dry_run=True))
        run.assert_not_called()

    @patch('app.services.python_installer.platform.freedesktop_os_release', return_value={'ID': 'debian'})
    @patch('app.services.python_installer.subprocess.run')
    def test_wrong_os_never_executes(self, run, release):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_python('3.11'))
        run.assert_not_called()

    @patch('app.services.python_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu'})
    @patch('app.services.python_installer.shutil.which', return_value='/usr/bin/tool')
    @patch('app.services.python_installer.subprocess.run', return_value=SimpleNamespace(returncode=100))
    def test_apt_failure_stops_subsequent_commands(self, run, *_):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertFalse(install_python('3.12'))
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('تم تثبيت', output.getvalue())

    def test_unprovided_versions_and_injection_rejected(self):
        for version in ('3.13', '3.12; echo bad'):
            with self.assertRaises(ValueError):
                build_plan(version)
