import json
import socket
import subprocess
import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import psutil
from django.test import SimpleTestCase

from infrastructure_engine.adapters.linux.local import (
    _cpu_info,
    _disk_info,
    _hardware_sensors,
    _memory_info,
    _network_connections,
    _network_interfaces,
    _network_routes,
    _provider_info,
    _running_systemd_services,
    _system_security,
    _top_processes,
    _run_readonly,
    collect_local_snapshot,
    get_local_server_load,
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

    @patch("infrastructure_engine.adapters.linux.local._run_readonly")
    @patch("infrastructure_engine.adapters.linux.local.shutil.which", return_value="/usr/bin/systemctl")
    def test_systemd_inventory_uses_fixed_bounded_read_only_command(self, which, run):
        run.return_value = "ssh.service loaded active running OpenSSH server\n"
        result = _running_systemd_services()
        self.assertEqual(result["running_count"], 1)
        self.assertEqual(result["items"][0]["unit"], "ssh.service")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"])
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

    @patch("infrastructure_engine.adapters.linux.local.psutil.process_iter")
    def test_process_inventory_caps_scan_and_preserves_missing_memory(self, process_iter):
        process_iter.return_value = iter(
            SimpleNamespace(info={
                "pid": pid, "name": "worker", "username": "svc",
                "status": "running", "memory_percent": None,
            })
            for pid in range(2001)
        )
        result = _top_processes()
        self.assertEqual(result["sampled_processes"], 2000)
        self.assertTrue(result["truncated"])
        self.assertIsNone(result["items"][0]["memory_percent"])


class LocalSnapshotDetailTests(SimpleTestCase):
    @patch("builtins.open")
    @patch("infrastructure_engine.adapters.linux.local.psutil.cpu_percent", side_effect=[20.5, [10.0, 31.0]])
    @patch("infrastructure_engine.adapters.linux.local.psutil.cpu_freq", return_value=SimpleNamespace(current=2200.0))
    @patch("infrastructure_engine.adapters.linux.local.psutil.cpu_count", side_effect=[4, 2])
    @patch("infrastructure_engine.adapters.linux.local.os.getloadavg", return_value=(0.2, 0.3, 0.4))
    def test_cpu_collector_returns_model_frequency_cores_and_live_usage(
        self, load, cores, frequency, usage, open_file
    ):
        open_file.return_value.__enter__.return_value = StringIO(
            "processor : 0\nmodel name : Example CPU 1000\n"
        )
        result = _cpu_info()
        self.assertEqual(result["model"], "Example CPU 1000")
        self.assertEqual(result["logical_cores"], 4)
        self.assertEqual(result["physical_cores"], 2)
        self.assertEqual(result["frequency_mhz"], 2200.0)
        self.assertEqual(result["usage_percent"], 20.5)
        self.assertEqual(result["per_core_usage_percent"], [10.0, 31.0])
        self.assertEqual(result["load_average"], [0.2, 0.3, 0.4])

    @patch("builtins.open")
    @patch("infrastructure_engine.adapters.linux.local.psutil.virtual_memory")
    @patch("infrastructure_engine.adapters.linux.local.psutil.swap_memory")
    def test_memory_collector_keeps_real_zero_and_optional_values(self, swap, memory, open_file):
        memory.return_value = SimpleNamespace(
            total=1024, used=700, available=324, percent=68.4
        )
        swap.return_value = SimpleNamespace(total=0, used=0, percent=0.0)
        open_file.return_value.__enter__.return_value = StringIO(
            "Cached: 100 kB\nBuffers: 0 kB\n"
        )
        result = _memory_info()
        self.assertEqual(result["cached_bytes"], 102400)
        self.assertEqual(result["buffers_bytes"], 0)
        self.assertEqual(result["swap_total_bytes"], 0)
        self.assertEqual(result["swap_percent"], 0.0)

    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_io_counters")
    @patch("infrastructure_engine.adapters.linux.local._run_readonly")
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_usage")
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_partitions")
    def test_storage_collects_filesystems_devices_and_io(
        self, partitions, disk_usage, run, disk_io
    ):
        partitions.return_value = [
            SimpleNamespace(device="/dev/sda1", mountpoint="/", fstype="ext4")
        ]
        disk_usage.return_value = SimpleNamespace(
            total=1000, used=400, free=600, percent=40.0
        )
        run.return_value = json.dumps({
            "blockdevices": [{
                "name": "sda", "type": "disk", "size": 2000, "model": "Disk",
                "rota": True, "children": [
                    {"name": "sda1", "type": "part", "size": 1000, "mountpoint": "/"}
                ],
            }]
        })
        disk_io.return_value = {
            "sda": SimpleNamespace(read_bytes=10, write_bytes=20, read_count=1, write_count=2)
        }
        result = _disk_info()
        self.assertEqual(result["filesystems"][0]["usage_percent"], 40.0)
        self.assertEqual(result["devices"][0]["name"], "sda")
        self.assertEqual(result["devices"][1]["parent"], "sda")
        self.assertEqual(result["disk_io"]["sda"]["write_bytes"], 20)
        self.assertTrue(result["devices_supported"])
        self.assertEqual(
            run.call_args.args[0],
            ["lsblk", "--json", "--bytes", "--output",
             "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL,ROTA"],
        )

    @patch("infrastructure_engine.adapters.linux.local.shutil.which", return_value="/usr/bin/lsblk")
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_io_counters", side_effect=OSError)
    @patch("infrastructure_engine.adapters.linux.local._run_readonly", return_value="not json")
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_usage")
    @patch("infrastructure_engine.adapters.linux.local.psutil.disk_partitions")
    def test_optional_block_device_errors_do_not_discard_filesystem_measurements(
        self, partitions, disk_usage, run, disk_io, which
    ):
        partitions.return_value = [
            SimpleNamespace(device="/dev/sda1", mountpoint="/", fstype="ext4")
        ]
        disk_usage.return_value = SimpleNamespace(
            total=1000, used=400, free=600, percent=40.0
        )
        result = _disk_info()
        self.assertEqual(len(result["filesystems"]), 1)
        self.assertEqual(result["disk_io"], {})
        self.assertFalse(result["devices_supported"])
        self.assertEqual(result["devices_reason"], "JSONDecodeError")

    @patch("infrastructure_engine.adapters.linux.local.shutil.which")
    def test_readonly_command_helper_enforces_output_limit_and_timeout(self, which):
        which.return_value = sys.executable
        self.assertEqual(
            _run_readonly(["python", "-c", "print('ok')"], timeout=2, max_output=16),
            "ok\n",
        )
        with self.assertRaises(ValueError):
            _run_readonly(
                ["python", "-c", "print('x' * 10000)"],
                timeout=2,
                max_output=16,
            )
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_readonly(
                ["python", "-c", "import time; time.sleep(2)"],
                timeout=0.1,
                max_output=16,
            )

    @patch("infrastructure_engine.adapters.linux.local.psutil.net_io_counters")
    @patch("infrastructure_engine.adapters.linux.local.psutil.net_if_stats")
    @patch("infrastructure_engine.adapters.linux.local.psutil.net_if_addrs")
    def test_network_interfaces_include_state_addresses_mac_and_counters(
        self, addresses, stats, counters
    ):
        addresses.return_value = {
            "eth0": [
                SimpleNamespace(family=socket.AF_INET, address="192.0.2.4"),
                SimpleNamespace(family=socket.AF_INET6, address="2001:db8::4%eth0"),
                SimpleNamespace(family=psutil.AF_LINK, address="02:00:00:00:00:01"),
            ]
        }
        stats.return_value = {
            "eth0": SimpleNamespace(isup=True, speed=1000, mtu=1500)
        }
        counters.return_value = {
            "eth0": SimpleNamespace(
                bytes_sent=100, bytes_recv=200, packets_sent=3, packets_recv=4
            )
        }
        result = _network_interfaces()["items"][0]
        self.assertTrue(result["is_up"])
        self.assertEqual(result["addresses"], ["192.0.2.4", "2001:db8::4"])
        self.assertEqual(result["mac_address"], "02:00:00:00:00:01")
        self.assertEqual(result["bytes_received"], 200)

    @patch("infrastructure_engine.adapters.linux.local._run_readonly", return_value=json.dumps([
        {"dst": "default", "gateway": "192.0.2.1", "dev": "eth0"},
        {"dst": "192.0.2.0/24", "dev": "eth0"},
    ]))
    def test_network_routes_report_default_gateway(self, run):
        result = _network_routes()
        self.assertEqual(result["default_gateway"], "192.0.2.1")
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(
            run.call_args.args[0], ["ip", "-j", "route", "show"]
        )

    @patch("infrastructure_engine.adapters.linux.local.psutil.net_connections")
    def test_connections_are_bounded_and_listening_ports_are_separated(self, connections):
        connection = SimpleNamespace(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=SimpleNamespace(ip="0.0.0.0", port=22),
            raddr=(),
            status=psutil.CONN_LISTEN,
            pid=12,
        )
        connections.return_value = [connection]
        result = _network_connections()
        self.assertEqual(result["listening_ports"][0]["local_address"]["port"], 22)
        self.assertEqual(result["listening_ports"][0]["pid"], 12)
        self.assertFalse(result["truncated"])

    @patch("infrastructure_engine.adapters.linux.local.psutil.net_connections")
    def test_connection_limit_prioritizes_listening_ports(self, connections):
        established = [
            SimpleNamespace(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                laddr=SimpleNamespace(ip="192.0.2.1", port=1000 + index),
                raddr=SimpleNamespace(ip="192.0.2.2", port=443),
                status=psutil.CONN_ESTABLISHED,
                pid=None,
            )
            for index in range(205)
        ]
        listener = SimpleNamespace(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=SimpleNamespace(ip="0.0.0.0", port=22),
            raddr=(),
            status=psutil.CONN_LISTEN,
            pid=1,
        )
        connections.return_value = established + [listener]
        result = _network_connections()
        self.assertEqual(len(result["items"]), 200)
        self.assertEqual(result["listening_ports"][0]["local_address"]["port"], 22)
        self.assertTrue(result["truncated"])

    @patch("infrastructure_engine.adapters.linux.local.psutil.sensors_battery", side_effect=NotImplementedError)
    @patch("infrastructure_engine.adapters.linux.local.psutil.sensors_temperatures", side_effect=NotImplementedError)
    def test_sensor_not_implemented_is_reported_as_unsupported(self, temperatures, battery):
        result = _hardware_sensors()
        self.assertFalse(result["supported"])
        self.assertFalse(result["temperature_supported"])
        self.assertFalse(result["battery_supported"])

    @patch("infrastructure_engine.adapters.linux.local._run_readonly", return_value=json.dumps({
        "ServerVersion": "27.0",
        "APIVersion": "1.46",
        "Driver": "overlay2",
        "OperatingSystem": "Ubuntu",
        "Architecture": "x86_64",
        "NCPU": 8,
        "MemTotal": 8192,
        "DockerRootDir": "/var/lib/docker",
    }))
    @patch("infrastructure_engine.adapters.linux.local.shutil.which")
    def test_provider_discovery_reports_actual_docker_engine_details(self, which, run):
        which.side_effect = lambda name: f"/usr/bin/{name}" if name in {
            "docker", "apt-get", "dpkg", "ansible", "systemctl", "smartctl"
        } else None
        result = _provider_info()
        self.assertEqual(result["docker"]["engine_status"], "available")
        self.assertEqual(result["docker"]["engine_version"], "27.0")
        self.assertEqual(result["docker"]["storage_driver"], "overlay2")
        self.assertEqual(result["docker"]["memory_bytes"], 8192)
        run.assert_called_once()

    @patch("infrastructure_engine.adapters.linux.local._run_readonly", return_value="Status: inactive\n")
    @patch("infrastructure_engine.adapters.linux.local.shutil.which", return_value="/usr/sbin/ufw")
    @patch("infrastructure_engine.adapters.linux.local.os.geteuid", return_value=1001)
    def test_security_context_reports_privilege_and_firewall_status(self, uid, which, run):
        result = _system_security()
        self.assertFalse(result["running_as_root"])
        self.assertEqual(result["effective_uid"], 1001)
        self.assertEqual(result["ufw"]["status"], "inactive")
        self.assertEqual(run.call_args.args[0], ["ufw", "status"])

    @patch("infrastructure_engine.adapters.linux.local._top_processes", return_value={"items": []})
    @patch("infrastructure_engine.adapters.linux.local._running_systemd_services", return_value={"items": []})
    @patch("infrastructure_engine.adapters.linux.local._hardware_sensors", return_value={
        "supported": False, "reason": "No sensors"
    })
    @patch("infrastructure_engine.adapters.linux.local._system_security", return_value={"running_as_root": False})
    @patch("infrastructure_engine.adapters.linux.local._provider_info", return_value={"docker": {"installed": False}})
    @patch("infrastructure_engine.adapters.linux.local._dns_servers", return_value=["192.0.2.53"])
    @patch("infrastructure_engine.adapters.linux.local._network_connections", return_value={"items": []})
    @patch("infrastructure_engine.adapters.linux.local._network_routes", return_value={"items": []})
    @patch("infrastructure_engine.adapters.linux.local._network_interfaces", return_value={"items": []})
    @patch("infrastructure_engine.adapters.linux.local._disk_info", return_value={"filesystems": []})
    @patch("infrastructure_engine.adapters.linux.local._memory_info", return_value={"total_bytes": 100})
    @patch("infrastructure_engine.adapters.linux.local._cpu_info", return_value={"usage_percent": 0.0})
    @patch("infrastructure_engine.adapters.linux.local._system_info", side_effect=PermissionError)
    def test_snapshot_retains_successful_sections_when_one_collector_fails(
        self, system, cpu, memory, disks, interfaces, routes, connections, dns,
        providers, security, sensors, services, processes,
    ):
        result = collect_local_snapshot()
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["data"]["system"])
        self.assertEqual(result["availability"]["system"]["status"], "unavailable")
        self.assertEqual(result["data"]["cpu"]["usage_percent"], 0.0)
        self.assertEqual(result["data"]["storage"]["filesystems"], [])
        self.assertEqual(result["data"]["disks"], [])
        self.assertEqual(result["availability"]["hardware_sensors"]["status"], "unsupported")
        self.assertGreater(result["duration_ms"], -1)
