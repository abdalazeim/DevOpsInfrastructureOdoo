"""
Health and monitoring telemetry models for Odoo multi-version infrastructure.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class ContainerHealth:
    name: str
    service: str
    status: str # "running" | "exited" | "unhealthy" | "healthy" | "missing"
    healthcheck_status: str # "healthy" | "unhealthy" | "starting" | "none"
    image: str
    uptime: str
    ports: List[str] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0

@dataclass
class ServiceEndpointHealth:
    service_name: str
    url: str
    status_code: Optional[int]
    is_up: bool
    response_time_ms: float
    error_message: Optional[str] = None

@dataclass
class SystemInfrastructureHealth:
    timestamp: datetime
    hostname: str
    docker_engine_active: bool
    docker_version: str
    proxy_network_active: bool
    containers: Dict[str, ContainerHealth] = field(default_factory=dict)
    endpoints: Dict[str, ServiceEndpointHealth] = field(default_factory=dict)
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_percent: float = 0.0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    all_healthy: bool = False
