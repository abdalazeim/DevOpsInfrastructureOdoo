"""
Docker and Docker Compose orchestration service.
"""
from typing import List, Dict, Any, Optional
from infrastructure_engine.models.operation import WorkflowStep

class DockerService:
    """Constructs safe, parameterized docker and docker compose commands."""

    @staticmethod
    def build_network_create_step(network_name: str = "proxy", subnet: str = "172.28.0.0/16") -> WorkflowStep:
        return WorkflowStep(
            id="create-proxy-network",
            name="Create Shared Proxy Network",
            description=f"Ensures bridge network '{network_name}' exists for Traefik routing",
            command=["docker", "network", "create", "--driver", "bridge", "--subnet", subnet, network_name],
        )

    @staticmethod
    def build_compose_config_step(compose_file: str, step_id: str = "validate-compose") -> WorkflowStep:
        return WorkflowStep(
            id=step_id,
            name="Validate Compose Config",
            description=f"Validates syntax of compose file: {compose_file}",
            command=["docker", "compose", "-f", compose_file, "config"],
        )

    @staticmethod
    def build_compose_up_step(compose_file: str, step_id: str = "launch-stack") -> WorkflowStep:
        return WorkflowStep(
            id=step_id,
            name="Deploy Docker Stack",
            description=f"Launches container services from {compose_file}",
            command=["docker", "compose", "-f", compose_file, "up", "-d"],
        )

    @staticmethod
    def build_compose_down_step(compose_file: str, remove_volumes: bool = False, step_id: str = "stop-stack") -> WorkflowStep:
        cmd = ["docker", "compose", "-f", compose_file, "down"]
        if remove_volumes:
            cmd.append("-v")
        return WorkflowStep(
            id=step_id,
            name="Stop Stack Containers",
            description=f"Stops and removes containers (Volumes removed: {remove_volumes})",
            command=cmd,
        )

    @staticmethod
    def build_container_logs_step(container_name: str, tail: int = 100) -> WorkflowStep:
        return WorkflowStep(
            id=f"logs-{container_name}",
            name=f"Fetch Logs for {container_name}",
            description=f"Retrieves recent {tail} lines from container logs",
            command=["docker", "logs", "--tail", str(tail), container_name],
        )
