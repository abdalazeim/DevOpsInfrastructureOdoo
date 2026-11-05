"""
Installation status tracking for infrastructure components.

Statuses:
- NOT CHECKED: Component has not been inspected yet
- ALREADY INSTALLED: Component is installed and verified
- READY TO INSTALL: Component is missing but ready for installation
- INSTALLING: Component is currently being installed
- INSTALLED: Component was just installed successfully
- FAILED: Component installation failed
- SKIPPED: Component was skipped (dependency failed or not requested)
- WARNING: Component installed but with non-critical issues
"""
from enum import Enum
from typing import Optional


class InstallationStatus(str, Enum):
    NOT_CHECKED = "NOT CHECKED"
    ALREADY_INSTALLED = "ALREADY INSTALLED"
    READY_TO_INSTALL = "READY TO INSTALL"
    INSTALLING = "INSTALLING"
    INSTALLED = "INSTALLED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


STATUS_COLORS = {
    InstallationStatus.NOT_CHECKED: "\033[0;37m",      # gray
    InstallationStatus.ALREADY_INSTALLED: "\033[0;32m", # green
    InstallationStatus.READY_TO_INSTALL: "\033[0;33m",  # yellow
    InstallationStatus.INSTALLING: "\033[0;36m",        # cyan
    InstallationStatus.INSTALLED: "\033[1;32m",         # bold green
    InstallationStatus.FAILED: "\033[0;31m",            # red
    InstallationStatus.SKIPPED: "\033[0;35m",           # magenta
    InstallationStatus.WARNING: "\033[1;33m",           # bold yellow
}


STATUS_SYMBOLS = {
    InstallationStatus.NOT_CHECKED: "?",
    InstallationStatus.ALREADY_INSTALLED: "OK",
    InstallationStatus.READY_TO_INSTALL: "READY",
    InstallationStatus.INSTALLING: "INSTALLING",
    InstallationStatus.INSTALLED: "DONE",
    InstallationStatus.FAILED: "FAILED",
    InstallationStatus.SKIPPED: "SKIP",
    InstallationStatus.WARNING: "WARN",
}


class ComponentStatusRecord:
    """Tracks the status of a single infrastructure component."""

    def __init__(
        self,
        name: str,
        category: str,
        version: Optional[str] = None,
        status: InstallationStatus = InstallationStatus.NOT_CHECKED,
        details: str = "",
        error: Optional[str] = None,
        log_file: Optional[str] = None,
        installed_at: Optional[str] = None,
        depends_on: Optional[list] = None,
    ):
        self.name = name
        self.category = category
        self.version = version
        self.status = status
        self.details = details
        self.error = error
        self.log_file = log_file
        self.installed_at = installed_at
        self.depends_on = depends_on or []

    @property
    def color(self) -> str:
        return STATUS_COLORS.get(self.status, "\033[0m")

    @property
    def symbol(self) -> str:
        return STATUS_SYMBOLS.get(self.status, "?")

    @property
    def can_install(self) -> bool:
        """Whether this component is eligible for installation."""
        return self.status in (
            InstallationStatus.READY_TO_INSTALL,
            InstallationStatus.FAILED,
        )

    @property
    def is_blocked(self) -> bool:
        """Whether installation is blocked by a failed dependency."""
        return self.status == InstallationStatus.SKIPPED

    def __repr__(self) -> str:
        return f"ComponentStatusRecord(name={self.name!r}, status={self.status.value})"
