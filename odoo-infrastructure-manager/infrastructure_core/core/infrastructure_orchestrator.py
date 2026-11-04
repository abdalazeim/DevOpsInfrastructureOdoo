"""
Centralized Service Layer for Odoo Infrastructure Manager.
Coordinates cross-module operations, provides unified access to system state,
and ensures consistent logging/auditing of all operations.
"""
import logging
import datetime
import subprocess
import os
import sys
from typing import Dict, Any, List, Optional
from infrastructure_engine.adapters.linux.local import get_local_server_load
from infrastructure_engine.services.traefik_manager import TraefikDockerManager
from infrastructure_engine.services.odoo_manager import OdooDockerManager

# Configure Centralized Logging
log_dir = os.path.expanduser("~/.local/log/odoo-infrastructure-manager")
try:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "infrastructure.log")
except Exception:
    log_file = "/tmp/infrastructure.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

class InfrastructureManager:
    """Unified Orchestrator for all infrastructure components."""
    
    def __init__(self, profile: Any):
        self.profile = profile
        self.logger = logging.getLogger("InfrastructureManager")

    def _safe_execute(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Executes a command safely with logging, timeouts, and error handling."""
        self.logger.info(f"Executing: {' '.join(command)}")
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                check=False
            )
            if result.returncode != 0:
                self.logger.error(f"Command failed (Code {result.returncode}): {result.stderr}")
                return {"success": False, "error": result.stderr, "code": result.returncode}
            
            self.logger.info("Command executed successfully.")
            return {"success": True, "output": result.stdout}
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s.")
            return {"success": False, "error": "Timeout", "code": 124}
        except Exception as e:
            self.logger.critical(f"System error executing command: {str(e)}")
            return {"success": False, "error": str(e), "code": 1}

    def generate_report(self) -> str:
        """Compiles system state into a comprehensive audit report."""
        report = f"# Infrastructure Audit Report - {datetime.datetime.now().isoformat()}\n\n"
        status = self.get_system_overview()
        report += f"## Docker Status: {'OK' if status['traefik']['container_status'] else 'Issue'}\n"
        report += f"## Odoo Status:\n- Odoo 17: {status['odoo']['odoo17']['container_status']}\n- Odoo 19: {status['odoo']['odoo19']['container_status']}\n"
        return report

    def get_system_overview(self) -> Dict[str, Any]:
        """Consolidated system status report."""
        return {
            'traefik': TraefikDockerManager.discover_environment(),
            'odoo': OdooDockerManager.discover_odoo_env(),
            'server_load': self._get_server_load()
        }

    def _get_server_load(self) -> Dict[str, Any]:
        return get_local_server_load()

    def run_operation(self, category: str, action: str, params: Dict[str, Any]) -> bool:
        """Centralized execution entry point with pre-flight checks."""
        self.logger.info(f"Initiating: {category} -> {action}")
        
        # Pre-flight check
        if not self._pre_flight_check():
            self.logger.critical("Pre-flight check failed! Aborting.")
            return False

        # Route actions
        if category == 'traefik':
            return self._handle_traefik(action, params)
        elif category.startswith('odoo'):
            return self._handle_odoo(category, action, params)
        elif category == 'health':
            return self._handle_health()
        
        return False

    def _pre_flight_check(self) -> bool:
        """Ensures the system is in a state where the operation can be run safely."""
        self.logger.info("Performing pre-flight system checks...")
        # Check if Docker is running
        if self._safe_execute(['docker', 'info'])['success'] is False:
            return False
        # Check storage (e.g. at least 1GB)
        # This is a placeholder for actual storage check
        return True

    def _handle_traefik(self, action: str, params: Dict[str, Any]) -> bool:
        if action == 'deploy':
            TraefikDockerManager.ensure_traefik_directories()
            return True
        elif action == 'restart':
            return self._safe_execute(['docker', 'restart', 'traefik'])['success']
        return False

    def _handle_odoo(self, category: str, action: str, params: Dict[str, Any]) -> bool:
        version = category.replace('odoo', '')
        return OdooDockerManager.lifecycle_action(version, action)
        
    def _handle_health(self) -> bool:
        self.logger.info("Running comprehensive health check...")
        return self._safe_execute(['docker', 'info'])['success']

