import unittest
from unittest.mock import patch

from app.services.runtime_inspector import inspect_docker, inspect_host


class TestRuntimeInspector(unittest.TestCase):
    @patch('app.services.runtime_inspector.glob.glob', return_value=[])
    @patch('app.services.runtime_inspector.shutil.which', return_value=None)
    def test_missing_postgres_does_not_report_client_as_server(self, *_):
        self.assertEqual(inspect_host('postgresql')['records'], [])

    @patch('app.services.runtime_inspector.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.runtime_inspector.probe', return_value=(1, 'permission denied'))
    def test_docker_permission_failure_is_not_reported_as_absence(self, *_):
        report = inspect_docker('python')
        self.assertEqual(report['records'], [])
        self.assertIn('permission denied', report['errors'])

    @patch('app.services.runtime_inspector.shutil.which', return_value='/usr/bin/docker')
    @patch('app.services.runtime_inspector.probe', side_effect=[
        (0, '{"Image":"postgres:17","Names":"database","Status":"Exited (0)"}\n{"Image":"odoo:17"}'),
        (0, '{"Repository":"postgres","Tag":"18"}')])
    def test_stopped_container_and_image_are_distinguished(self, *_):
        records = inspect_docker('postgresql')['records']
        self.assertEqual([r['kind'] for r in records], ['container', 'image'])
        self.assertEqual(records[0]['status'], 'Exited (0)')

    def test_unknown_component_rejected(self):
        with self.assertRaises(ValueError):
            inspect_host('unknown')
