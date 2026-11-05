import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from app.services.portainer_service import build_plan, inspect_portainer, install_portainer


class TestPortainerService(unittest.TestCase):
    def test_http_and_bind_mount_default_with_edge(self):
        command = build_plan()[1]
        self.assertIn('9000:9000', command)
        self.assertIn('/srv/portainer:/data', command)
        self.assertNotIn('portainer_data:/data', command)
        self.assertIn('8000:8000', command)

    def test_no_edge_omits_8000(self):
        command = build_plan(edge=False)[1]
        self.assertIn('9000:9000', command)
        self.assertNotIn('8000:8000', command)

    def test_custom_port(self):
        command = build_plan(port=9001, edge=False)[1]
        self.assertIn('9001:9000', command)
        self.assertNotIn('8000:8000', command)

    def test_invalid_and_conflicting_ports(self):
        for port in (0, 65536, '9443'):
            with self.assertRaises(ValueError):
                build_plan(port)
        with self.assertRaises(ValueError):
            build_plan(8000, edge=True)

    @patch('app.services.portainer_service.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.portainer_service.probe', return_value=(1, 'permission denied'))
    def test_daemon_error_is_not_missing(self, *_):
        self.assertEqual(inspect_portainer()['status'], 'error')

    @patch('app.services.portainer_service.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.portainer_service.probe', return_value=(0, '{"Names":"custom","Image":"portainer/portainer-ce:lts","Status":"Exited"}'))
    def test_stopped_renamed_container_is_installed(self, *_):
        self.assertEqual(inspect_portainer()['status'], 'installed')

    @patch('app.services.portainer_service.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.portainer_service.probe', return_value=(0, '{"Names":"portainer","Image":"nginx"}'))
    def test_name_collision(self, *_):
        self.assertEqual(inspect_portainer()['status'], 'conflict')

    @patch('app.services.docker_installer.subprocess.run')
    def test_preview_never_runs_docker(self, run):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(install_portainer(dry_run=True))
        run.assert_not_called()

    @patch('app.services.portainer_service.platform.system', return_value='Linux')
    @patch('app.services.portainer_service.inspect_portainer', return_value={'status': 'installed', 'error': ''})
    @patch('app.services.portainer_service.run_step')
    def test_existing_instance_blocks_install(self, run, *_):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(install_portainer())
        run.assert_not_called()

    @patch('app.services.portainer_service.platform.system', return_value='Linux')
    @patch('app.services.portainer_service.inspect_portainer', return_value={'status': 'missing', 'error': ''})
    @patch('app.services.portainer_service.socket.socket')
    @patch('app.services.portainer_service.run_step')
    @patch('app.services.portainer_service.probe', return_value=(0, 'exited'))
    def test_failed_start_never_reports_success(self, probe, run, sock, *_):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertFalse(install_portainer())
        self.assertEqual(run.call_count, 2)
        self.assertNotIn('Portainer container is running', output.getvalue())
