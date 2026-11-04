import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from app.services.postgresql_installer import build_plan, install_postgresql


class TestPostgresqlInstaller(unittest.TestCase):
    def test_selected_version_and_optional_vector(self):
        for version in ('15', '16', '17', '18'):
            for vector in (False, True):
                commands = build_plan(version, with_pgvector=vector, privileged=True)
                self.assertTrue(any(f'postgresql-{version}' in c and f'postgresql-client-{version}' in c for c in commands))
                self.assertEqual(any(f'postgresql-{version}-pgvector' in c for c in commands), vector)
                self.assertFalse(any('psql' in c or 'sudo' in c for c in commands))

    @patch('app.services.postgresql_installer.subprocess.run')
    def test_dry_run_does_not_execute(self, run):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_postgresql('18', with_pgvector=True, dry_run=True))
        run.assert_not_called()

    @patch('app.services.postgresql_installer.platform.freedesktop_os_release', return_value={'ID': 'ubuntu'})
    @patch('app.services.postgresql_installer.shutil.which', return_value='/usr/bin/tool')
    @patch('app.services.postgresql_installer.subprocess.run', side_effect=[SimpleNamespace(returncode=0), SimpleNamespace(returncode=100)])
    def test_failure_stops_before_repository_setup(self, run, *_):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_postgresql('16'))
        self.assertEqual(run.call_count, 2)

    @patch('app.services.postgresql_installer.platform.freedesktop_os_release', return_value={'ID': 'debian'})
    @patch('app.services.postgresql_installer.subprocess.run')
    def test_non_ubuntu_cannot_install(self, run, *_):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_postgresql('17'))
        run.assert_not_called()

    def test_invalid_version(self):
        for version in ('19', '16; echo bad'):
            with self.assertRaises(ValueError):
                build_plan(version)
