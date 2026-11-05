"""
Reorganized Menu System for Odoo Infrastructure Manager.

Organizes all functionality into 11 professional categories:
1. Dashboard - System Overview, Installation Progress, Infrastructure Health, Recent Events
2. System - System Information, OS & Updates, Hardware & Storage, Users & Permissions
3. Setup & Installation - Pre-Installation Checks, Install Missing Components, Installation History, Failed Installations
4. Infrastructure - Docker Management, Docker Network Management, Traefik Management, PostgreSQL Management, DNS & SSL Verification
5. Odoo - Odoo 17/18/19 Management, Instance Deployment, Diagnosis & Repair
6. Automation - Ansible Installation & Configuration, Jenkins CI/CD, Deployment Pipelines, Configuration Profiles
7. Data Protection - Backup Management, Restore Management, Backup Verification, Disaster Recovery
8. Operations - Monitoring & Logs, Infrastructure Health Check, Troubleshooting, Error Diagnosis & Auto-Repair
9. Reports - Infrastructure Report, Installation Report, Service Health Report, Backup & Recovery Report, Audit History
10. Command Notebook - Browse, edit, save, search, and copy commands (read-only, never executes)
11. Installation Pipeline - Dependency-aware sequential installation with verification
12. System Cleanup & Uninstall - Full system cleanup and deep uninstall of all project components
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

# ANSI color codes
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class MenuItem:
    """A single menu item with an action handler."""
    key: str
    label: str
    handler: Optional[Callable] = None
    description: str = ""
    submenu: Optional["MenuCategory"] = None


@dataclass
class MenuCategory:
    """A menu category containing multiple items."""
    key: str
    label: str
    icon: str = ""
    description: str = ""
    items: List[MenuItem] = field(default_factory=list)

    def get_item(self, key: str) -> Optional[MenuItem]:
        for item in self.items:
            if item.key == key:
                return item
        return None


class MenuSystem:
    """
    Professional menu system with categorized organization.

    Provides a consistent interface for displaying menus, handling
    navigation, and executing actions.
    """

    def __init__(self, tui_instance):
        self.tui = tui_instance
        self.categories: List[MenuCategory] = []
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the complete menu structure."""
        self.categories = [
            MenuCategory(
                key="1",
                label="Dashboard",
                icon="",
                description="System overview, installation progress, infrastructure health, recent events",
                items=[
                    MenuItem("1", "System Overview", self.tui.handle_system_information,
                             "View server hostname, IP, OS, disk, Docker status"),
                    MenuItem("2", "Installation Progress", self.tui.handle_installation_progress,
                             "View current installation status of all components"),
                    MenuItem("3", "Infrastructure Health", self.tui.handle_infrastructure_health,
                             "Run comprehensive health check on all services"),
                    MenuItem("4", "Recent Events", self.tui.handle_recent_events,
                             "View recent installation and operation events"),
                ],
            ),
            MenuCategory(
                key="2",
                label="System",
                icon="",
                description="System information, OS & updates, hardware & storage, users & permissions",
                items=[
                    MenuItem("1", "System Information", self.tui.handle_system_information,
                             "Detailed system and hardware information"),
                    MenuItem("2", "Operating System & Updates", self.tui.handle_os_updates,
                             "Check OS version and apply system updates"),
                    MenuItem("3", "Hardware & Storage", self.tui.handle_hardware_storage,
                             "View CPU, RAM, disk usage and storage devices"),
                    MenuItem("4", "Users & Permissions", self.tui.handle_users_permissions,
                             "Manage system users, groups, and permissions"),
                ],
            ),
            MenuCategory(
                key="3",
                label="Setup & Installation",
                icon="",
                description="Pre-installation checks, install missing components, installation history, failed installations",
                items=[
                    MenuItem("1", "Pre-Installation Checks", self.tui.run_preflight_checks,
                             "Verify internet, repositories, disk space, privileges, compatibility"),
                    MenuItem("2", "Install Missing Components", self.tui.handle_install_missing_components,
                             "Install components that are missing or not ready"),
                    MenuItem("3", "Installation History", self.tui.handle_installation_history,
                             "View history of past installations and reports"),
                    MenuItem("4", "Failed Installations", self.tui.handle_failed_installations,
                             "View and retry failed component installations"),
                ],
            ),
            MenuCategory(
                key="4",
                label="Infrastructure",
                icon="",
                description="Docker management, Docker network management, Traefik management, PostgreSQL management, DNS & SSL verification",
                items=[
                    MenuItem("1", "Docker Management", self.tui.handle_docker_management,
                             "Manage Docker containers, images, and daemon"),
                    MenuItem("2", "Docker Network Management", self.tui.handle_network_management,
                             "Manage Docker proxy and internal networks"),
                    MenuItem("3", "Traefik Management", self.tui.handle_traefik_management,
                             "Manage Traefik reverse proxy and routing"),
                    MenuItem("4", "PostgreSQL Management", self.tui.handle_postgresql_management,
                             "Manage PostgreSQL databases for Odoo instances"),
                    MenuItem("5", "DNS & SSL Verification", self.tui.handle_dns_ssl_verification,
                             "Verify domain DNS resolution and SSL certificates"),
                ],
            ),
            MenuCategory(
                key="5",
                label="Odoo",
                icon="",
                description="Odoo 17/18/19 management, instance deployment, diagnosis & repair",
                items=[
                    MenuItem("1", "Odoo 17 Management", self.tui.handle_odoo17_management,
                             "Deploy and manage Odoo 17 instances"),
                    MenuItem("2", "Odoo 18 Management", self.tui.handle_odoo18_management,
                             "Deploy and manage Odoo 18 instances"),
                    MenuItem("3", "Odoo 19 Management", self.tui.handle_odoo19_management,
                             "Deploy and manage Odoo 19 instances"),
                    MenuItem("4", "Instance Deployment", self.tui.handle_odoo_instance_deployment,
                             "Deploy new Odoo instances across versions"),
                    MenuItem("5", "Diagnosis & Repair", self.tui.handle_odoo_diagnosis,
                             "Diagnose and repair Odoo installation issues"),
                ],
            ),
            MenuCategory(
                key="6",
                label="Automation",
                icon="",
                description="Ansible installation & configuration, Jenkins CI/CD, deployment pipelines, configuration profiles",
                items=[
                    MenuItem("1", "Ansible Installation & Configuration", self.tui.handle_ansible_install,
                             "Install Ansible and configure automation"),
                    MenuItem("2", "Jenkins CI/CD", self.tui.handle_jenkins_install,
                             "Install and manage Jenkins CI/CD server"),
                    MenuItem("3", "Deployment Pipelines", self.tui.handle_deployment_pipelines,
                             "View and trigger deployment pipelines"),
                    MenuItem("4", "Configuration Profiles", self.tui.handle_configuration_profiles,
                             "Manage infrastructure configuration profiles"),
                ],
            ),
            MenuCategory(
                key="7",
                label="Data Protection",
                icon="",
                description="Backup management, restore management, backup verification, disaster recovery",
                items=[
                    MenuItem("1", "Backup Management", self.tui.handle_backup_management,
                             "Create backups of Odoo databases and filestores"),
                    MenuItem("2", "Restore Management", self.tui.handle_restore_management,
                             "Restore Odoo databases from backups"),
                    MenuItem("3", "Backup Verification", self.tui.handle_backup_verification,
                             "Verify backup integrity and completeness"),
                    MenuItem("4", "Disaster Recovery", self.tui.handle_disaster_recovery,
                             "Full infrastructure disaster recovery procedures"),
                ],
            ),
            MenuCategory(
                key="8",
                label="Operations",
                icon="",
                description="Monitoring & logs, infrastructure health check, troubleshooting, error diagnosis & auto-repair",
                items=[
                    MenuItem("1", "Monitoring & Logs", self.tui.handle_monitoring_logs,
                             "View logs for Traefik, Odoo, and infrastructure services"),
                    MenuItem("2", "Infrastructure Health Check", self.tui.handle_infrastructure_health,
                             "Run comprehensive infrastructure health diagnostic"),
                    MenuItem("3", "Troubleshooting", self.tui.handle_troubleshooting,
                             "Diagnose common infrastructure issues"),
                    MenuItem("4", "Error Diagnosis & Auto-Repair", self.tui.handle_error_diagnosis,
                             "Automatically diagnose and repair component errors"),
                ],
            ),
            MenuCategory(
                key="9",
                label="Reports",
                icon="",
                description="Infrastructure report, installation report, service health report, backup & recovery report, audit history",
                items=[
                    MenuItem("1", "Infrastructure Report", self.tui.handle_generate_infrastructure_report,
                             "Generate comprehensive infrastructure audit report"),
                    MenuItem("2", "Installation Report", self.tui.handle_installation_report,
                             "Generate installation component status report"),
                    MenuItem("3", "Service Health Report", self.tui.handle_service_health_report,
                             "Generate service health status report"),
                    MenuItem("4", "Backup & Recovery Report", self.tui.handle_backup_recovery_report,
                             "Generate backup and recovery status report"),
                    MenuItem("5", "Audit History", self.tui.handle_audit_history,
                             "View audit history of infrastructure changes"),
                ],
            ),
            MenuCategory(
                key="10",
                label="Command Notebook",
                icon="",
                description="Browse, edit, save, search, and copy commands (read-only, never executes)",
                items=[
                    MenuItem("1", "Open Command Notebook", self.tui.handle_command_notebook,
                             "Launch the interactive command notebook library"),
                ],
            ),
            MenuCategory(
                key="11",
                label="Installation Pipeline",
                icon="",
                description="Dependency-aware sequential installation with per-component verification",
                items=[
                    MenuItem("1", "Run Installation Pipeline", self.tui.handle_installation_pipeline,
                             "Run the full sequential installation pipeline with Odoo version selection"),
                ],
            ),
            MenuCategory(
                key="12",
                label="System Cleanup & Uninstall",
                icon="",
                description="Full system cleanup and deep uninstall of all project components (backups preserved)",
                items=[
                    MenuItem("1", "Full Cleanup & Deep Uninstall", self.tui.handle_full_cleanup,
                             "Remove all project-installed components. Backups are always preserved."),
                ],
            ),
        ]

    def display_main_menu(self) -> None:
        """Display the main menu with all categories."""
        print(f"\n{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                     ODOO INFRASTRUCTURE MANAGER                            ║")
        print("║              Professional Infrastructure Management System                 ║")
        print("║   Ubuntu 22.04+ | Docker | Traefik v3.7 | Odoo 17/18/19 | Ansible | Jenkins  ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(f"{RESET}")
        print(f"{BOLD}Host:{RESET} {self.tui.profile.server.hostname} ({self.tui.profile.server.ip_or_host})  |  "
              f"{BOLD}Profile:{RESET} {self.tui.profile.profile_name}  |  "
              f"{BOLD}Timezone:{RESET} {self.tui.profile.server.timezone}")
        print("─" * 78)

        for cat in self.categories:
            print(f"\n{CYAN}{BOLD}[{cat.key}] {cat.label}{RESET}")
            if cat.description:
                print(f"    {DIM}{cat.description}{RESET}")
            for item in cat.items:
                print(f"      {item.key}. {item.label}")
                if item.description:
                    print(f"         {DIM}{item.description}{RESET}")

        print(f"\n  {BOLD}0.{RESET} Exit")
        print(f"{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")

    def get_choice(self) -> str:
        """Get user choice from the main menu."""
        max_key = str(len(self.categories))
        return input(f"\n{BOLD}Select a category [1-{max_key}] or 0 to exit: {RESET}").strip()

    def get_submenu_choice(self, category: MenuCategory) -> str:
        """Get user choice from a submenu."""
        max_key = str(len(category.items))
        return input(f"\n{BOLD}Select an option [1-{max_key}] or 0 to return: {RESET}").strip()

    def display_category(self, category: MenuCategory) -> None:
        """Display a category's submenu."""
        print(f"\n{CYAN}{BOLD}")
        print("═" * 70)
        print(f"  {category.label}")
        print("═" * 70)
        print(f"{RESET}")
        print(f"{DIM}{category.description}{RESET}\n")

        for item in category.items:
            print(f"  {BOLD}{item.key}.{RESET} {item.label}")
            if item.description:
                print(f"     {DIM}{item.description}{RESET}")

        print(f"\n  {BOLD}0.{RESET} Return to Main Menu")
        print(f"{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")

    def execute_item(self, item: MenuItem) -> None:
        """Execute a menu item's handler."""
        if item.handler:
            try:
                item.handler()
            except Exception as exc:
                print(f"\n{RED}Error executing '{item.label}': {exc}{RESET}")
        elif item.submenu:
            self.display_category(item.submenu)
        else:
            print(f"\n{YELLOW}No handler defined for '{item.label}'.{RESET}")

    def get_category(self, key: str) -> Optional[MenuCategory]:
        """Get a category by its key."""
        for cat in self.categories:
            if cat.key == key:
                return cat
        return None
