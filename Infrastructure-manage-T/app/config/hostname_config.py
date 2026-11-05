"""
Centralized Hostname & Domain Configuration.

Single source of truth for server hostname and primary domain.
Reads from System Information at startup and propagates to all
dependent components (Traefik, Jenkins, Odoo, Docker Compose, Ansible, etc.).

Subdomains are generated dynamically from the configured primary domain:
  - jenkins.<primary-domain>
  - traefik.<primary-domain>
  - odoo17-1.<primary-domain>
  - odoo17-2.<primary-domain>
  - odoo19-1.<primary-domain>
  - odoo19-2.<primary-domain>
"""

from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HostnameConfig:
    """Centralized hostname and domain configuration."""

    hostname: str
    primary_domain: str
    ip_address: str = "127.0.0.1"

    # Derived subdomains (generated dynamically, never hardcoded)
    @property
    def jenkins_domain(self) -> str:
        return f"jenkins.{self.primary_domain}"

    @property
    def traefik_domain(self) -> str:
        return f"traefik.{self.primary_domain}"

    @property
    def odoo17_instance1_domain(self) -> str:
        return f"odoo17-1.{self.primary_domain}"

    @property
    def odoo17_instance2_domain(self) -> str:
        return f"odoo17-2.{self.primary_domain}"

    @property
    def odoo19_instance1_domain(self) -> str:
        return f"odoo19-1.{self.primary_domain}"

    @property
    def odoo19_instance2_domain(self) -> str:
        return f"odoo19-2.{self.primary_domain}"

    @property
    def odoo18_instance1_domain(self) -> str:
        return f"odoo18-1.{self.primary_domain}"

    @property
    def odoo18_instance2_domain(self) -> str:
        return f"odoo18-2.{self.primary_domain}"

    # Legacy subdomain names for backward compatibility (Odoo 17 used odoo1/odoo2)
    @property
    def odoo17_legacy_instance1_domain(self) -> str:
        return f"odoo1.{self.primary_domain}"

    @property
    def odoo17_legacy_instance2_domain(self) -> str:
        return f"odoo2.{self.primary_domain}"

    # Legacy subdomain names for backward compatibility (Odoo 19 used odoo1/odoo2)
    @property
    def odoo19_legacy_instance1_domain(self) -> str:
        return f"odoo1.{self.primary_domain}"

    @property
    def odoo19_legacy_instance2_domain(self) -> str:
        return f"odoo2.{self.primary_domain}"

    def subdomain(self, service: str, instance: Optional[str] = None) -> str:
        """Generate a subdomain for a service, optionally with instance suffix."""
        if instance:
            return f"{service}-{instance}.{self.primary_domain}"
        return f"{service}.{self.primary_domain}"

    def validate(self) -> list[str]:
        """Validate hostname and domain. Returns list of error messages."""
        errors: list[str] = []

        if not self.hostname or not self.hostname.strip():
            errors.append("Hostname is empty")
        elif not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$', self.hostname):
            errors.append(f"Invalid hostname: '{self.hostname}'")

        if not self.primary_domain or not self.primary_domain.strip():
            errors.append("Primary domain is empty")
        elif not re.match(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$',
            self.primary_domain,
        ):
            errors.append(f"Invalid primary domain: '{self.primary_domain}'")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


# ---------------------------------------------------------------------------
# Module-level singleton (populated at setup time)
# ---------------------------------------------------------------------------

_config: Optional[HostnameConfig] = None


def get_config() -> HostnameConfig:
    """Return the centralized hostname configuration. Raises if not initialized."""
    if _config is None:
        raise RuntimeError(
            "HostnameConfig not initialized. Call detect_and_configure() first."
        )
    return _config


def set_config(config: HostnameConfig) -> None:
    """Set the centralized hostname configuration."""
    global _config
    _config = config


def detect_system_hostname() -> str:
    """Detect the actual server hostname from the OS."""
    try:
        return socket.gethostname()
    except Exception:
        return "localhost"


def detect_system_domain() -> str:
    """Attempt to detect the configured domain from system info."""
    # Try /etc/hostname first (may contain fqdn)
    try:
        with open("/etc/hostname", "r", encoding="utf-8") as f:
            h = f.read().strip()
            if h and "." in h:
                return h.split(".", 1)[1]
    except Exception:
        pass

    # Try resolv.conf domain/search
    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("domain ") or line.startswith("search "):
                    parts = line.split()
                    if len(parts) > 1:
                        return parts[1]
    except Exception:
        pass

    return ""


def detect_and_configure(
    hostname: Optional[str] = None,
    primary_domain: Optional[str] = None,
    ip_address: Optional[str] = None,
    interactive: bool = True,
) -> HostnameConfig:
    """
    Detect or accept hostname and domain, validate, and store as the
    centralized configuration. If interactive, prompts user to confirm/edit.
    """
    global _config

    detected_hostname = hostname or detect_system_hostname()
    detected_domain = primary_domain or detect_system_domain() or detected_hostname

    if ip_address is None:
        try:
            ip_address = socket.gethostbyname(detected_hostname)
        except Exception:
            ip_address = "127.0.0.1"

    config = HostnameConfig(
        hostname=detected_hostname,
        primary_domain=detected_domain,
        ip_address=ip_address,
    )

    errors = config.validate()
    if errors:
        if interactive:
            print("\n" + "=" * 60)
            print(" HOSTNAME / DOMAIN CONFIGURATION REQUIRED")
            print("=" * 60)
            print("\nDetected system information:")
            print(f"  Hostname: {detected_hostname}")
            print(f"  Domain:   {detected_domain or '(not detected)'}")
            print(f"  IP:       {ip_address}")
            print("\nValidation issues:")
            for e in errors:
                print(f"  - {e}")
            print("\nPlease review and correct the values below.\n")

            user_hostname = input(f"Server hostname [{detected_hostname}]: ").strip()
            if user_hostname:
                detected_hostname = user_hostname

            user_domain = input(f"Primary domain [{detected_domain or 'localhost'}]: ").strip()
            if user_domain:
                detected_domain = user_domain
            elif not detected_domain:
                detected_domain = "localhost"
                print(
                    "  [WARN] No domain provided. Using fallback: localhost "
                    "(change this before production deployment)"
                )

            try:
                user_ip = input(f"IP address [{ip_address}]: ").strip()
                if user_ip:
                    ip_address = user_ip
            except Exception:
                pass

            config = HostnameConfig(
                hostname=detected_hostname,
                primary_domain=detected_domain,
                ip_address=ip_address,
            )

            errors = config.validate()
            if errors:
                print("\nConfiguration still invalid:")
                for e in errors:
                    print(f"  - {e}")
                print("Cannot proceed without valid hostname and domain.\n")
                raise ValueError(f"Invalid hostname/domain configuration: {errors}")
        else:
            raise ValueError(
                f"Invalid hostname/domain configuration: detected_hostname={detected_hostname}, "
                f"primary_domain={detected_domain}, errors={errors}"
            )

    print("\n" + "=" * 60)
    print(" HOSTNAME & DOMAIN CONFIGURATION")
    print("=" * 60)
    print(f"  Hostname:        {config.hostname}")
    print(f"  Primary domain:  {config.primary_domain}")
    print(f"  IP address:      {config.ip_address}")
    print(f"  Jenkins:         {config.jenkins_domain}")
    print(f"  Traefik:         {config.traefik_domain}")
    print(f"  Odoo 17-1:       {config.odoo17_instance1_domain}")
    print(f"  Odoo 17-2:       {config.odoo17_instance2_domain}")
    print(f"  Odoo 19-1:       {config.odoo19_instance1_domain}")
    print(f"  Odoo 19-2:       {config.odoo19_instance2_domain}")
    print("=" * 60 + "\n")

    set_config(config)
    return config


def reset_config() -> None:
    """Reset the centralized configuration (mainly for testing)."""
    global _config
    _config = None
