from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from infrastructure_engine.adapters.linux.local import (
    _running_systemd_services, _top_processes, get_local_server_load,
)


class LinuxDiscoveryAdapterTests(SimpleTestCase):
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_usage", return_value=SimpleNamespace(percent=50.0))
    @patch("infrastructure_engine.adapters.linux.local.psutil.virtual_memory", return_value=SimpleNamespace(used=4 * 1024**3, total=16 * 1024**3))
    @patch("infrastructure_engine.adapters.linux.local.psutil.cpu_percent", return_value=17.5)
    def test_legacy_resource_summary_uses_live_measurements(self, cpu, memory, disk):
        result = get_local_server_load()
        self.assertEqual(result, {
            "cpu": "17.5%", "ram": "4.0GB/16.0GB", "disk": "50.0%",
            "source": "live-local-host", "available": True,
        })

    @patch("infrastructure_engine.adapters.linux.local.psutil.cpu_percent", side_effect=OSError("unavailable"))
    def test_legacy_resource_summary_marks_failed_measurement_unavailable(self, cpu):
        result = get_local_server_load()
        self.assertFalse(result["available"])
        self.assertNotIn("cpu", result)
        self.assertEqual(result["error"], "OSError")

    @patch("infrastructure_engine.adapters.linux.local.subprocess.run")
    @patch("infrastructure_engine.adapters.linux.local.shutil.which", return_value="/usr/bin/systemctl")
    def test_systemd_inventory_uses_fixed_bounded_read_only_command(self, which, run):
        run.return_value = SimpleNamespace(stdout="ssh.service loaded active running OpenSSH server\n")
        result = _running_systemd_services()
        self.assertEqual(result["running_count"], 1)
        self.assertEqual(result["items"][0]["unit"], "ssh.service")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["/usr/bin/systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"])
        self.assertTrue(kwargs["check"])
        self.assertLessEqual(kwargs["timeout"], 5)

    @patch("infrastructure_engine.adapters.linux.local.shutil.which", return_value=None)
    def test_service_inventory_reports_unsupported_without_systemctl(self, which):
        result = _running_systemd_services()
        self.assertFalse(result["supported"])
        self.assertEqual(result["items"], [])

    @patch("infrastructure_engine.adapters.linux.local.psutil.process_iter")
    def test_process_inventory_is_bounded_and_does_not_collect_command_lines(self, process_iter):
        process_iter.return_value = [
            SimpleNamespace(info={"pid": i, "name": f"process-{i}", "username": "svc", "status": "running", "memory_percent": float(i)})
            for i in range(30)
        ]
        result = _top_processes()
        self.assertEqual(result["sampled_processes"], 30)
        self.assertEqual(len(result["items"]), 20)
        self.assertEqual(result["items"][0]["pid"], 29)
        self.assertNotIn("cmdline", result["items"][0])
        process_iter.assert_called_once_with(attrs=["pid", "name", "username", "status", "memory_percent"])
