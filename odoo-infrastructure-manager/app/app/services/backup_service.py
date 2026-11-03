"""
Database backup and restore orchestration service.
"""
from typing import Optional, List
from infrastructure_engine.models.operation import WorkflowStep

class BackupService:
    """Builds commands for safe database dumps and verification."""

    @staticmethod
    def build_backup_step(version: str, db_name: str, retention_count: int = 7) -> WorkflowStep:
        return WorkflowStep(
            id=f"backup-odoo{version}",
            name=f"Backup Odoo {version} Database & Filestore",
            description=f"Creates verified compressed pg_dump and filestore archive for {db_name}",
            command=["bash", "automation/scripts/backup-db.sh", version, db_name, str(retention_count)],
        )

    @staticmethod
    def build_restore_step(version: str, dump_file_path: str, target_db: str, force: bool = False) -> WorkflowStep:
        cmd = ["bash", "automation/scripts/restore-db.sh", version, dump_file_path, target_db]
        if force:
            cmd.append("--force")

        return WorkflowStep(
            id=f"restore-odoo{version}",
            name=f"Restore Odoo {version} Database",
            description=f"Restores dump {dump_file_path} into {target_db} with safety backup",
            command=cmd,
        )
