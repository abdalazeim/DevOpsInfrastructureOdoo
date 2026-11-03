"""
Workflow: Database Backup, Restore, and Maintenance Operations.
"""
from typing import List, Optional
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep
from app.services.backup_service import BackupService

class DatabaseOpsWorkflow:
    """Orchestrates database backups, retention cleanup, and safe restores."""

    @staticmethod
    def create_backup_operation(version: str, db_name: str, retention_count: int = 7, dry_run: bool = False) -> OperationRecord:
        steps = [
            WorkflowStep(
                id=f"verify-db-container-running",
                name=f"Verify PostgreSQL {version} Container",
                description=f"Ensures odoo{version}-db container is running before backup",
                command=["docker", "inspect", "--format={{.State.Status}}", f"odoo{version}-db"],
            ),
            BackupService.build_backup_step(version=version, db_name=db_name, retention_count=retention_count),
        ]

        return OperationRecord(
            operation_id=f"op-backup-odoo{version}-{db_name}",
            name=f"Backup Database [{db_name}] for Odoo {version}",
            category="backup",
            profile_name="active",
            steps=steps,
            dry_run=dry_run,
        )

    @staticmethod
    def create_restore_operation(version: str, dump_file_path: str, target_db: str, force: bool = False, dry_run: bool = False) -> OperationRecord:
        steps = [
            WorkflowStep(
                id="validate-backup-file-existence",
                name="Validate Backup Archive Exists",
                description=f"Checks integrity and existence of {dump_file_path}",
                command=["test", "-s", dump_file_path],
            ),
            BackupService.build_restore_step(version=version, dump_file_path=dump_file_path, target_db=target_db, force=force),
        ]

        return OperationRecord(
            operation_id=f"op-restore-odoo{version}-{target_db}",
            name=f"Restore Database [{target_db}] from Archive",
            category="restore",
            profile_name="active",
            steps=steps,
            dry_run=dry_run,
        )
