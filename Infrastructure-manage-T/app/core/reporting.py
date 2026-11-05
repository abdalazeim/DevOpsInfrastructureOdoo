"""
Professional Reporting System for Odoo Infrastructure Manager.

Generates comprehensive reports:
- Installation Report: Component status, versions, durations, errors
- Service Health Report: Health checks for all infrastructure services
- Backup & Recovery Report: Backup status, retention, recovery points
- Audit History: Historical audit reports from docs directory
- Infrastructure Report: Full system configuration snapshot
"""
from __future__ import annotations

import os
import glob
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.installation_status import (
    InstallationStatus,
    ComponentStatusRecord,
    STATUS_COLORS,
    STATUS_SYMBOLS,
)
from app.core.server_setup import ServerSetupWorkflow
from app.models.profile import InfrastructureProfile

# ANSI color codes
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    content: str
    status: Optional[InstallationStatus] = None


class InfrastructureReporter:
    """
    Generates professional reports for infrastructure status.

    Supports text, JSON, and markdown output formats.
    """

    def __init__(self, profile: InfrastructureProfile, project_root: str):
        self.profile = profile
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()

    def generate_installation_report(self, dry_run: bool = False) -> Dict[str, Any]:
        """Generate a comprehensive installation status report."""
        setup = ServerSetupWorkflow(self.profile, dry_run=dry_run, use_sudo=True)
        setup.inspect_all()
        result = setup.generate_report()

        report = {
            "report_type": "installation",
            "timestamp": self.timestamp,
            "profile": self.profile.profile_name,
            "host": self.profile.server.hostname,
            "ip": self.profile.server.ip_or_host,
            "overall_success": result["overall_success"],
            "summary": {
                "total": result["total"],
                "success": result["success_count"],
                "failed": result["failure_count"],
                "skipped": result["skip_count"],
                "warning": result["warning_count"],
                "ready": len(result["ready"]),
                "not_checked": len(result["not_checked"]),
            },
            "components": [],
        }

        for name, record in sorted(result["components"].items()):
            report["components"].append({
                "name": name,
                "category": record.category,
                "status": record.status.value,
                "version": record.version,
                "details": record.details,
                "error": record.error,
                "depends_on": record.depends_on,
                "log_file": record.log_file,
            })

        return report

    def generate_service_health_report(self) -> Dict[str, Any]:
        """Generate a service health status report."""
        from app.services.health_service import HealthService
        step = HealthService.build_health_check_step()

        report = {
            "report_type": "service_health",
            "timestamp": self.timestamp,
            "profile": self.profile.profile_name,
            "host": self.profile.server.hostname,
            "services": [],
        }

        # Check each service
        services_to_check = [
            ("docker", ["docker", "--version"]),
            ("docker-compose", ["bash", "-c", "docker compose version"]),
            ("traefik", ["bash", "-c", "docker ps -a --filter name=traefik --format '{{.Names}}' | grep -q '^traefik$'"]),
            ("jenkins", ["bash", "-c", "docker ps -a --filter name=jenkins --format '{{.Names}}' | grep -q '^jenkins$'"]),
            ("odoo17", ["bash", "-c", "docker ps -a --filter name=odoo17-instance1 --format '{{.Names}}' | grep -q ."]),
            ("odoo18", ["bash", "-c", "docker ps -a --filter name=odoo18-instance1 --format '{{.Names}}' | grep -q ."]),
            ("odoo19", ["bash", "-c", "docker ps -a --filter name=odoo19-instance1 --format '{{.Names}}' | grep -q ."]),
        ]

        import subprocess
        for name, cmd in services_to_check:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                healthy = result.returncode == 0
                report["services"].append({
                    "name": name,
                    "healthy": healthy,
                    "status": "HEALTHY" if healthy else "UNHEALTHY",
                    "output": result.stdout.strip()[:200] if healthy else result.stderr.strip()[:200],
                })
            except Exception as exc:
                report["services"].append({
                    "name": name,
                    "healthy": False,
                    "status": "ERROR",
                    "output": str(exc)[:200],
                })

        return report

    def generate_backup_recovery_report(self) -> Dict[str, Any]:
        """Generate a backup and recovery status report."""
        from app.services.system_backup import SystemBackupService

        report = {
            "report_type": "backup_recovery",
            "timestamp": self.timestamp,
            "profile": self.profile.profile_name,
            "backup_root": self.profile.backup.backup_root,
            "retention_count": self.profile.backup.retention_count,
            "backups": [],
        }

        backup_root = self.profile.backup.backup_root
        if os.path.exists(backup_root):
            for entry in sorted(os.listdir(backup_root)):
                full_path = os.path.join(backup_root, entry)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                    report["backups"].append({
                        "name": entry,
                        "path": full_path,
                        "size_bytes": size,
                        "size_mb": round(size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(mtime).isoformat(),
                    })

        try:
            snap = SystemBackupService.create_full_snapshot()
            report["latest_snapshot"] = {
                "archive_file": snap.get("archive_file", ""),
                "sha256": snap.get("sha256", ""),
            }
        except Exception as exc:
            report["snapshot_error"] = str(exc)

        return report

    def generate_audit_history(self) -> Dict[str, Any]:
        """Generate an audit history report from existing audit files."""
        docs_dir = os.path.join(self.project_root, "docs")
        audit_files = []

        if os.path.exists(docs_dir):
            for af in sorted(glob.glob(os.path.join(docs_dir, "audit_report_*.md")), key=os.path.getmtime, reverse=True):
                with open(af, "r") as f:
                    content = f.read()
                audit_files.append({
                    "file": os.path.basename(af),
                    "path": af,
                    "modified": datetime.fromtimestamp(os.path.getmtime(af)).isoformat(),
                    "content_preview": content[:500],
                })

        return {
            "report_type": "audit_history",
            "timestamp": self.timestamp,
            "profile": self.profile.profile_name,
            "audit_files": audit_files,
            "total_audits": len(audit_files),
        }

    def generate_infrastructure_report(self) -> Dict[str, Any]:
        """Generate a comprehensive infrastructure audit report."""
        return {
            "report_type": "infrastructure",
            "timestamp": self.timestamp,
            "profile": self.profile.profile_name,
            "host": self.profile.server.hostname,
            "ip": self.profile.server.ip_or_host,
            "timezone": self.profile.server.timezone,
            "traefik_domain": self.profile.traefik.dashboard_domain,
            "odoo17_domain": self.profile.odoo17.domain,
            "odoo18_domain": self.profile.odoo18.domain,
            "odoo19_domain": self.profile.odoo19.domain,
            "postgres_versions": {
                "17": "16",
                "18": "17",
                "19": "18",
            },
            "backup_retention": self.profile.backup.retention_count,
            "security": {
                "enforce_https": self.profile.security.enforce_https,
                "isolate_postgres": self.profile.security.isolate_postgres_network,
                "strict_permissions": self.profile.security.strict_file_permissions,
            },
        }

    def print_report(self, report: Dict[str, Any]) -> None:
        """Print a report to the terminal in a formatted way."""
        rtype = report.get("report_type", "unknown")

        print(f"\n{CYAN}{BOLD}")
        print("═" * 78)
        titles = {
            "installation": "INSTALLATION STATUS REPORT",
            "service_health": "SERVICE HEALTH REPORT",
            "backup_recovery": "BACKUP & RECOVERY REPORT",
            "audit_history": "AUDIT HISTORY REPORT",
            "infrastructure": "INFRASTRUCTURE AUDIT REPORT",
        }
        print(f"  {titles.get(rtype, 'REPORT').center(70)}")
        print("═" * 78)
        print(f"{RESET}")
        print(f"{BOLD}Profile:{RESET} {report.get('profile', 'N/A')}  |  "
              f"{BOLD}Host:{RESET} {report.get('host', 'N/A')}  |  "
              f"{BOLD}Time:{RESET} {report.get('timestamp', 'N/A')[:19]}")
        print("─" * 78)

        if rtype == "installation":
            self._print_installation_report(report)
        elif rtype == "service_health":
            self._print_service_health_report(report)
        elif rtype == "backup_recovery":
            self._print_backup_recovery_report(report)
        elif rtype == "audit_history":
            self._print_audit_history_report(report)
        elif rtype == "infrastructure":
            self._print_infrastructure_report(report)

        print(f"\n{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")

    def _print_installation_report(self, report: Dict[str, Any]) -> None:
        s = report["summary"]
        print(f"{BOLD}Summary:{RESET}")
        print(f"  Total: {s['total']}  |  "
              f"{GREEN}Success: {s['success']}{RESET}  |  "
              f"{RED}Failed: {s['failed']}{RESET}  |  "
              f"{YELLOW}Skipped: {s['skipped']}{RESET}  |  "
              f"{YELLOW}Warning: {s['warning']}{RESET}  |  "
              f"{DIM}Ready: {s['ready']}{RESET}  |  "
              f"{DIM}Not Checked: {s['not_checked']}{RESET}")
        print(f"\n  {BOLD}Overall: {GREEN if report['overall_success'] else RED}"
              f"{'PASS' if report['overall_success'] else 'FAIL'}{RESET}")
        print(f"\n{BOLD}Components:{RESET}")
        print("  " + "-" * 76)
        for comp in report["components"]:
            status = comp["status"]
            color = STATUS_COLORS.get(InstallationStatus(status), "")
            symbol = STATUS_SYMBOLS.get(InstallationStatus(status), "?")
            print(f"  {color}[{symbol}] {status}{RESET}  {comp['name']:<30} "
                  f"(v{comp['version'] or 'N/A'})  {comp.get('details', '')}")
            if comp.get("error"):
                print(f"    {RED}Error: {comp['error']}{RESET}")

    def _print_service_health_report(self, report: Dict[str, Any]) -> None:
        print(f"\n{BOLD}Services:{RESET}")
        print("  " + "-" * 76)
        for svc in report["services"]:
            healthy = svc["healthy"]
            color = GREEN if healthy else RED
            status = "HEALTHY" if healthy else "UNHEALTHY"
            print(f"  {color}[{status}]{RESET}  {svc['name']:<20} {svc.get('output', '')[:50]}")

    def _print_backup_recovery_report(self, report: Dict[str, Any]) -> None:
        print(f"\n{BOLD}Backup Root:{RESET} {report['backup_root']}")
        print(f"{BOLD}Retention Count:{RESET} {report['retention_count']}")
        print(f"\n{BOLD}Backups ({len(report['backups'])}):{RESET}")
        if report["backups"]:
            print("  " + "-" * 76)
            for b in report["backups"]:
                print(f"  {b['name']:<40} {b['size_mb']:>8} MB  {b['modified'][:19]}")
        else:
            print(f"  {YELLOW}No backups found.{RESET}")
        if report.get("latest_snapshot"):
            print(f"\n{BOLD}Latest Snapshot:{RESET} {report['latest_snapshot']['archive_file']}")
            print(f"  SHA256: {report['latest_snapshot']['sha256'][:16]}...")
        if report.get("snapshot_error"):
            print(f"\n{RED}Snapshot Error: {report['snapshot_error']}{RESET}")

    def _print_audit_history_report(self, report: Dict[str, Any]) -> None:
        print(f"\n{BOLD}Total Audits:{RESET} {report['total_audits']}")
        if report["audit_files"]:
            print("  " + "-" * 76)
            for af in report["audit_files"]:
                print(f"  {af['file']:<50} {af['modified'][:19]}")
        else:
            print(f"  {YELLOW}No audit reports found.{RESET}")

    def _print_infrastructure_report(self, report: Dict[str, Any]) -> None:
        print(f"\n{BOLD}Traefik Domain:{RESET} {report['traefik_domain']}")
        print(f"{BOLD}Odoo 17 Domain:{RESET} {report['odoo17_domain']}")
        print(f"{BOLD}Odoo 18 Domain:{RESET} {report['odoo18_domain']}")
        print(f"{BOLD}Odoo 19 Domain:{RESET} {report['odoo19_domain']}")
        print(f"\n{BOLD}PostgreSQL Versions:{RESET}")
        for odoo_ver, pg_ver in report["postgres_versions"].items():
            print(f"  Odoo {odoo_ver} -> PostgreSQL {pg_ver}")
        print(f"\n{BOLD}Security Settings:{RESET}")
        print(f"  Enforce HTTPS: {report['security']['enforce_https']}")
        print(f"  Isolate PostgreSQL: {report['security']['isolate_postgres']}")
        print(f"  Strict File Permissions: {report['security']['strict_permissions']}")
        print(f"\n{BOLD}Backup Retention:{RESET} {report['backup_retention']} days")

    def save_report(self, report: Dict[str, Any], output_dir: str = "reports") -> str:
        """Save a report to a JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rtype = report.get("report_type", "report")
        filename = f"{rtype}_report_{ts}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        return filepath
