"""
Pre-flight system checks and host environment validation.
"""
import shutil
import socket
import subprocess
from typing import Dict, List, Any

class SystemCheckItem:
    def __init__(self, name: str, passed: bool, message: str, is_critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.is_critical = is_critical

class SystemValidator:
    """Performs real or simulated host pre-flight checks."""

    @staticmethod
    def check_docker_installed() -> SystemCheckItem:
        docker_path = shutil.which("docker")
        if not docker_path:
            return SystemCheckItem("Docker Engine", False, "Docker executable not found in PATH", is_critical=True)
        try:
            res = subprocess.run([docker_path, "--version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return SystemCheckItem("Docker Engine", True, res.stdout.strip(), is_critical=True)
        except Exception as e:
            return SystemCheckItem("Docker Engine", False, f"Docker check failed: {e}", is_critical=True)
        return SystemCheckItem("Docker Engine", False, "Docker command failed", is_critical=True)

    @staticmethod
    def check_compose_plugin() -> SystemCheckItem:
        docker_path = shutil.which("docker")
        if not docker_path:
            return SystemCheckItem("Docker Compose", False, "Docker not installed", is_critical=True)
        try:
            res = subprocess.run([docker_path, "compose", "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return SystemCheckItem("Docker Compose", True, res.stdout.strip(), is_critical=True)
        except Exception as e:
            return SystemCheckItem("Docker Compose", False, f"Compose check failed: {e}", is_critical=True)
        return SystemCheckItem("Docker Compose", False, "Docker Compose plugin v2 is not active", is_critical=True)

    @staticmethod
    def check_port_free(port: int, host: str = "127.0.0.1") -> SystemCheckItem:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.bind((host, port))
                return SystemCheckItem(f"Port {port} Availability", True, f"Port {port} is free and ready", is_critical=False)
            except OSError:
                return SystemCheckItem(f"Port {port} Availability", False, f"Port {port} is already in use by another service!", is_critical=True)

    @staticmethod
    def check_disk_space(path: str = "/", min_free_gb: float = 5.0) -> SystemCheckItem:
        try:
            total, used, free = shutil.disk_usage(path)
            free_gb = free / (1024 ** 3)
            if free_gb >= min_free_gb:
                return SystemCheckItem("Disk Capacity", True, f"Free space: {free_gb:.1f} GB (Requirement: >{min_free_gb} GB)", is_critical=True)
            else:
                return SystemCheckItem("Disk Capacity", False, f"Low disk space: {free_gb:.1f} GB available (Requires at least {min_free_gb} GB)", is_critical=True)
        except Exception as e:
            return SystemCheckItem("Disk Capacity", False, f"Could not determine disk usage: {e}", is_critical=False)

    @classmethod
    def run_preflight_checks(cls, ports: List[int] = None) -> List[SystemCheckItem]:
        if ports is None:
            ports = [80, 443]
        results = [
            cls.check_docker_installed(),
            cls.check_compose_plugin(),
            cls.check_disk_space(),
        ]
        for port in ports:
            results.append(cls.check_port_free(port))
        return results
