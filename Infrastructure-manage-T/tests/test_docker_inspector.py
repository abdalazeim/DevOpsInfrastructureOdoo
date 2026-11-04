import unittest
from unittest.mock import patch

from app.services.docker_inspector import inspect_engine


class TestDockerInspector(unittest.TestCase):
    @patch('app.services.docker_inspector.shutil.which', return_value=None)
    @patch('app.services.docker_inspector.probe')
    def test_missing_does_not_execute_commands(self, probe, which):
        self.assertEqual(inspect_engine()['status'], 'missing')
        probe.assert_not_called()

    @patch('app.services.docker_inspector.shutil.which', side_effect=[None, '/usr/bin/dockerd'])
    def test_daemon_without_client_is_not_missing(self, which):
        self.assertEqual(inspect_engine()['status'], 'client_missing')

    def report(self, info):
        with patch('app.services.docker_inspector.shutil.which', return_value='/usr/bin/docker'), patch(
            'app.services.docker_inspector.probe', side_effect=[
                (0, 'Docker version 27'), (0, 'remote'), (0, 'Docker Compose v2'), info]):
            return inspect_engine()

    def test_access_denied_is_not_missing(self):
        self.assertEqual(self.report((1, 'permission denied'))['status'], 'permission_denied')

    def test_unreachable_is_not_missing(self):
        self.assertEqual(self.report((1, 'Cannot connect'))['status'], 'unreachable')

    def test_server_version_not_client_version(self):
        report = self.report((0, '{"ServerVersion":"28.0", "Containers":0}'))
        self.assertEqual(report['status'], 'running')
        self.assertEqual(report['server_version'], '28.0')
        self.assertEqual(report['details']['Containers'], 0)

    def test_malformed_output_is_not_healthy(self):
        self.assertEqual(self.report((0, 'bad json'))['status'], 'invalid_response')
