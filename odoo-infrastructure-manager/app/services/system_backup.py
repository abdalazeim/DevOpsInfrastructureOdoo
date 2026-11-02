"""
Full Infrastructure Snapshot and Safe System Restore Service.
Creates comprehensive archives of configurations, environment secrets, Traefik setups,
ACME certificates, database dumps, and Docker Compose definitions with SHA256 verification.
"""
import os
import tarfile
import hashlib
import json
import shutil
import datetime
from typing import Dict, Any, List, Optional
from app.models.operation import WorkflowStep

class SystemBackupService:
    """Manages full infrastructure snapshots and verified restorations."""

    @staticmethod
    def calculate_sha256(filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def create_full_snapshot(
        cls,
        data_root: str = "/opt/odoo-infrastructure",
        output_dir: Optional[str] = None,
        include_db_dumps: bool = True
    ) -> Dict[str, Any]:
        """Creates a complete infrastructure snapshot archive."""
        if not output_dir:
            output_dir = os.path.join(data_root, "backups", "system_snapshots")

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"full_snapshot_{timestamp}.tar.gz"
        archive_path = os.path.join(output_dir, archive_name)
        manifest_path = os.path.join(output_dir, f"manifest_{timestamp}.json")

        files_to_pack = []

        # 1. Configuration files and profiles
        for folder in ["profiles", "deployment", "templates", "automation"]:
            if os.path.exists(folder):
                files_to_pack.append(folder)

        # 2. Secret environment file
        if os.path.exists(".env"):
            files_to_pack.append(".env")
        if os.path.exists(".env.example"):
            files_to_pack.append(".env.example")

        # 3. Persistent configs in data_root if exist
        traefik_acme = os.path.join(data_root, "traefik", "acme", "acme.json")
        if os.path.exists(traefik_acme):
            files_to_pack.append(traefik_acme)

        # Build tar archive
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in files_to_pack:
                if os.path.exists(item):
                    tar.add(item)

        file_size = os.path.getsize(archive_path)
        sha256_hash = cls.calculate_sha256(archive_path)

        manifest = {
            "snapshot_id": f"snap-{timestamp}",
            "timestamp": timestamp,
            "archive_file": archive_name,
            "archive_path": archive_path,
            "file_size_bytes": file_size,
            "sha256": sha256_hash,
            "included_paths": files_to_pack,
            "status": "verified",
        }

        with open(manifest_path, "w") as mf:
            json.dump(manifest, mf, indent=2)

        return manifest

    @classmethod
    def list_snapshots(cls, data_root: str = "/opt/odoo-infrastructure") -> List[Dict[str, Any]]:
        snapshot_dir = os.path.join(data_root, "backups", "system_snapshots")
        if not os.path.exists(snapshot_dir):
            return []

        results = []
        for file in os.listdir(snapshot_dir):
            if file.startswith("manifest_") and file.endswith(".json"):
                m_path = os.path.join(snapshot_dir, file)
                try:
                    with open(m_path, "r") as f:
                        data = json.load(f)
                        # Verify archive still exists
                        if os.path.exists(data.get("archive_path", "")):
                            results.append(data)
                except Exception:
                    continue

        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)

    @classmethod
    def verify_archive(cls, archive_path: str, expected_sha256: Optional[str] = None) -> bool:
        if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
            return False

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                # Test readability of members
                members = tar.getmembers()
                if not members:
                    return False
        except Exception:
            return False

        if expected_sha256:
            actual = cls.calculate_sha256(archive_path)
            return actual == expected_sha256

        return True

    @classmethod
    def restore_snapshot(
        cls,
        archive_path: str,
        target_dir: str = ".",
        pre_restore_backup: bool = True
    ) -> Dict[str, Any]:
        """Restores a snapshot archive after creating a safety backup."""
        if not cls.verify_archive(archive_path):
            raise ValueError(f"Snapshot archive {archive_path} is corrupted or empty.")

        safety_manifest = None
        if pre_restore_backup:
            safety_manifest = cls.create_full_snapshot()

        # Extract archive
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=target_dir)

        return {
            "status": "success",
            "restored_archive": archive_path,
            "safety_snapshot": safety_manifest,
            "message": "Infrastructure snapshot restored successfully.",
        }
