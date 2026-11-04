from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from infrastructure_engine.adapters.ssh.discovery import collect_ssh_snapshot


class _RemoteFile:
    def __init__(self, value):
        self.value = value.encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.value if limit < 0 else self.value[:limit]


class RemoteLinuxDiscoveryTests(SimpleTestCase):
    def test_remote_collection_uses_only_fixed_probes_and_returns_bounded_sections(self):
        client = MagicMock()
        sftp = MagicMock()
        client.open_sftp.return_value = sftp
        files = {
            "/etc/os-release": 'NAME="Ubuntu"\nVERSION_ID="24.04"\n',
            "/etc/hostname": "vps-01\n",
            "/proc/uptime": "12345.50 10000.00\n",
            "/proc/cpuinfo": "processor : 0\nprocessor : 1\n",
            "/proc/loadavg": "0.10 0.20 0.30 1/100 200\n",
            "/proc/meminfo": "MemTotal: 1000 kB\nMemAvailable: 400 kB\nSwapTotal: 100 kB\nSwapFree: 50 kB\n",
            "/etc/resolv.conf": "nameserver 192.0.2.53\n",
        }
        cpu_stats = iter((
            "cpu 100 0 100 800 0 0 0 0\n",
            "cpu 110 0 105 895 0 0 0 0\n",
        ))

        def open_remote(path, mode):
            if path == "/proc/stat":
                return _RemoteFile(next(cpu_stats))
            return _RemoteFile(files[path])

        sftp.open.side_effect = open_remote
        existing = {"/usr/bin/systemctl", "/usr/bin/ps", "/usr/bin/docker"}
        sftp.stat.side_effect = lambda path: object() if path in existing else (_ for _ in ()).throw(OSError())
        commands = {
            "uname -srm": "Linux 6.8.0 x86_64\n",
            "df -P -B1 /": "Filesystem 1B-blocks Used Available Use% Mounted on\n/dev/sda1 100000 40000 60000 40% /\n",
            "ip -o address show": "1: lo inet 127.0.0.1/8 scope host lo\n2: eth0 inet 192.0.2.20/24 scope global eth0\n",
            "systemctl list-units --type=service --state=running --no-legend --no-pager": "ssh.service loaded active running OpenSSH server\n",
            "ps -eo pid=,comm=,user=,state=,%mem= --sort=-%mem": "1 systemd root S 1.0\n22 app odoo S 2.0\n",
        }
        calls = []

        def exec_fixed(command, timeout):
            calls.append(command)
            stdout = MagicMock()
            stdout.read.return_value = commands[command].encode()
            stdout.channel = MagicMock()
            stdout.channel.recv_exit_status.return_value = 0
            stderr = MagicMock()
            stderr.read.return_value = b""
            return MagicMock(), stdout, stderr

        client.exec_command.side_effect = exec_fixed
        host = MagicMock(hostname="192.0.2.20")
        with patch("infrastructure_engine.adapters.ssh.discovery.SSHConnectionAdapter._connect_authenticated",
                   return_value=(client, 8)):
            result = collect_ssh_snapshot(host)

        self.assertEqual(result["source"], "remote-ssh-linux")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["system"]["distribution"], "Ubuntu 24.04")
        self.assertEqual(result["data"]["system"]["hostname"], "vps-01")
        self.assertEqual(result["data"]["cpu"]["logical_cores"], 2)
        self.assertEqual(result["data"]["services"]["items"][0]["unit"], "ssh.service")
        self.assertEqual(result["data"]["processes"]["items"][0]["pid"], 1)
        self.assertNotIn("cmdline", result["data"]["processes"]["items"][0])
        self.assertEqual(set(calls), set(commands))
        client.close.assert_called_once_with()
        sftp.close.assert_called_once_with()
