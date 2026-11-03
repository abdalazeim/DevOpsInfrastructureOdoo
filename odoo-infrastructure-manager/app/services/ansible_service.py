"""
Ansible automation service for baseline Ubuntu server configuration.
"""
from typing import Dict, Any, List, Optional
from app.models.operation import WorkflowStep

class AnsibleService:
    """Builds Ansible runner commands with idempotency and dry-run (--check) support."""

    @staticmethod
    def build_playbook_step(
        playbook_path: str = "automation/ansible/playbook.yml",
        inventory_path: str = "automation/ansible/inventory.ini",
        extra_vars: Optional[Dict[str, Any]] = None,
        check_mode: bool = False,
        tags: Optional[List[str]] = None,
        step_id: str = "ansible-baseline"
    ) -> WorkflowStep:
        cmd = ["ansible-playbook", "-i", inventory_path, playbook_path]

        if check_mode:
            cmd.append("--check")

        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        if extra_vars:
            import json
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])

        return WorkflowStep(
            id=step_id,
            name="Run Ansible Baseline Playbook",
            description=f"Applies server baseline tasks from {playbook_path} (Check mode: {check_mode})",
            command=cmd,
        )
