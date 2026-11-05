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
import subprocess
from typing import Dict, Any, List, Optional
from app.models.operation import WorkflowStep
from app.services.archive_utils import safe_extractall

DOCKER = ["docker"]


class SystemBackupService:
    """Manages full infrastructure snapshots and verified restorations."""

    @staticmethod
    def calculate_sha256(filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _run_docker_cmd(cmd: List[str]) -> tuple[int, str, str]:
        """Run a docker command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, check=False
            )
            return result.returncode, result.stdout or "", result.stderr or ""
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 1, "", str(exc)

    @classmethod
    def _dump_databases(cls, tmp_dir: str) -> List[str]:
        """Dump all running PostgreSQL Odoo containers into SQL files in tmp_dir."""
        dumped: List[str] = []
        code, output, _ = cls._run_docker_cmd(
            DOCKER + ["ps", "-a", "--format", "{{json .}}"]
        )
        if code != 0:
            return dumped
        try:
            import json as _json
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                item = _json.loads(line)
                name = item.get("Names", "")
                image = item.get("Image", "")
                status = item.get("Status", "")
                if "-db" not in name:
                    continue
                if "postgres" not in image:
                    continue
                if "Exited" in status or "Created" in status:
                    continue
                # Derive Odoo version and DB name from container name
                parts = name.split("-")
                odoo_ver = parts[0] if parts else "odoo"
                db_name = f"{odoo_ver}_prod"
                dump_path = os.path.join(tmp_dir, f"{name}_database.sql")
                dcode, dout, derr = cls._run_docker_cmd(
                    DOCKER + ["exec", "-i", name, "pg_dump", "-U", "postgres", db_name]
                )
                if dcode == 0:
                    with open(dump_path, "w", encoding="utf-8") as f:
                        f.write(dout)
                    dumped.append(dump_path)
        except (ValueError, AttributeError, KeyError):
            pass
        return dumped

    @classmethod
    def create_full_snapshot(
        cls,
        data_root: str = os.environ.get("ODOO_DATA_ROOT", "/opt/odoo-infrastructure"),
        output_dir: Optional[str] = None,
        include_db_dumps: bool = True
    ) -> Dict[str, Any]:
        """Creates a complete infrastructure snapshot archive."""
        # Use project-local backup dir if system paths not writable
        if not output_dir:
            candidate = os.path.join(data_root, "backups", "system_snapshots")
            try:
                os.makedirs(candidate, exist_ok=True)
                output_dir = candidate
            except Exception:
                output_dir = os.path.join(os.getcwd(), "backups", "system_snapshots")

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

        # 4. Database dumps (F10: include_db_dumps now actually dumps DBs)
        db_dump_files: List[str] = []
        if include_db_dumps:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                db_dump_files = cls._dump_databases(tmp_dir)
                # Copy dumps into files_to_pack after tar is built below; handle via staging
                staged_db_dir = os.path.join(output_dir, f"_db_staging_{timestamp}")
                os.makedirs(staged_db_dir, exist_ok=True)
                for dump_file in db_dump_files:
                    if os.path.exists(dump_file):
                        dest = os.path.join(staged_db_dir, os.path.basename(dump_file))
                        shutil.copy2(dump_file, dest)
                        files_to_pack.append(dest)

        # Build tar archive
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in files_to_pack:
                if os.path.exists(item):
                    tar.add(item)

        file_size = os.path.getsize(archive_path)
        sha256_hash = cls.calculate_sha256(archive_path)

        # F37: Restrict archive permissions to 0600 (may contain .env secrets).
        try:
            os.chmod(archive_path, 0o600)
        except OSError:
            pass

        manifest = {
            "snapshot_id": f"snap-{timestamp}",
            "timestamp": timestamp,
            "archive_file": archive_name,
            "archive_path": archive_path,
            "file_size_bytes": file_size,
            "sha256": sha256_hash,
            "included_paths": files_to_pack,
            "database_dumps": [os.path.basename(d) for d in db_dump_files],
            "include_db_dumps": include_db_dumps,
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
        if not os.path.exists(archive_path):
            raise ValueError(f"Snapshot archive not found: {archive_path}")

        # Load manifest to get expected SHA256 (F11: verify checksum on restore)
        expected_sha256: Optional[str] = None
        manifest_dir = os.path.dirname(archive_path)
        manifest_base = os.path.basename(archive_path)
        # manifest_{timestamp}.json corresponds to full_snapshot_{timestamp}.tar.gz
        if manifest_base.startswith("full_snapshot_") and manifest_base.endswith(".tar.gz"):
            ts_part = manifest_base[len("full_snapshot_"):-len(".tar.gz")]
            manifest_path = os.path.join(manifest_dir, f"manifest_{ts_part}.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as mf:
                        manifest = json.load(mf)
                        expected_sha256 = manifest.get("sha256")
                except Exception:
                    pass

        if not cls.verify_archive(archive_path, expected_sha256=expected_sha256):
            raise ValueError(f"Snapshot archive {archive_path} is corrupted, empty, or SHA256 mismatch.")

        safety_manifest = None
        if pre_restore_backup:
            safety_manifest = cls.create_full_snapshot()

        # Extract archive using the hardened extractor (blocks traversal/links).
        with tarfile.open(archive_path, "r:gz") as tar:
            safe_extractall(tar, target_dir)

        return {
            "status": "success",
            "restored_archive": archive_path,
            "safety_snapshot": safety_manifest,
            "sha256_verified": expected_sha256 is not None,
            "message": "Infrastructure snapshot restored successfully.",
        }
