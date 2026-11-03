export type Language = 'ar' | 'en';

export interface ServerConfig {
  hostname: string;
  ip_or_host: string;
  timezone: string;
  ssh_user: string;
  ssh_port: number;
}

export interface PathsConfig {
  project_root: string;
  data_root: string;
  backup_root: string;
}

export interface NetworkConfig {
  proxy_network_name: string;
  proxy_subnet: string;
  enable_ipv6: boolean;
}

export interface TraefikConfig {
  enabled: boolean;
  image: string;
  dashboard_enabled: boolean;
  dashboard_domain: string;
  acme_email: string;
  acme_challenge: 'http' | 'tls-alpn';
  http_port: number;
  https_port: number;
}

export interface DatabaseConfig {
  engine: string;
  name: string;
  user: string;
  password_env_var: string;
  admin_password_env_var: string;
  internal_port: number;
  expose_public_port: boolean;
}

export interface OdooInstanceConfig {
  enabled: boolean;
  version: '17' | '18' | '19';
  domain: string;
  image: string;
  workers: number;
  memory_limit_soft: string;
  memory_limit_hard: string;
  database: DatabaseConfig;
}

export interface BackupConfig {
  enabled: boolean;
  cron_schedule: string;
  retention_count: number;
  include_filestore: boolean;
  compression: string;
  verify_checksum: boolean;
}

export interface SecurityConfig {
  strict_file_permissions: boolean;
  acme_mode_600: boolean;
  isolate_postgres_network: boolean;
  enforce_https: boolean;
}

export interface InfrastructureProfile {
  profile_name: string;
  description: string;
  version: string;
  server: ServerConfig;
  paths: PathsConfig;
  network: NetworkConfig;
  traefik: TraefikConfig;
  odoo17: OdooInstanceConfig;
  odoo18: OdooInstanceConfig;
  odoo19: OdooInstanceConfig;
  backup: BackupConfig;
  security: SecurityConfig;
}

export type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

export interface WorkflowStepItem {
  id: string;
  name: string;
  name_ar: string;
  description: string;
  description_ar: string;
  command: string[];
  status: StepStatus;
  duration?: number;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
}

export type OperationCategory =
  | 'system_info'
  | 'health'
  | 'install_components'
  | 'docker_mgmt'
  | 'traefik'
  | 'network_mgmt'
  | 'odoo17'
  | 'odoo18'
  | 'odoo19'
  | 'postgres_mgmt'
  | 'dns_ssl'
  | 'backup'
  | 'restore'
  | 'monitoring_logs'
  | 'profiles'
  | 'troubleshooting'
  | 'infra_report'
  | 'server_prep'
  | 'full_deploy';

export interface OperationPlan {
  id: string;
  name: string;
  name_ar: string;
  category: OperationCategory;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  steps: WorkflowStepItem[];
  dryRun?: boolean;
}

export interface BackupMetadata {
  id: string;
  version: '17' | '18' | '19';
  database: string;
  timestamp: string;
  dump_file: string;
  dump_size_bytes: number;
  sha256: string;
  has_filestore: boolean;
  filestore_size_bytes?: number;
  status: 'verified' | 'failed';
}

export interface ContainerRuntimeHealth {
  name: string;
  service: string;
  status: 'running' | 'restarting' | 'exited' | 'not_deployed';
  healthcheck: 'healthy' | 'unhealthy' | 'starting' | 'none';
  image: string;
  ports: string[];
  uptime: string;
  cpu_percent: number;
  memory_mb: number;
  network: string[];
}

export type ComponentAuditStatus = 'installed' | 'missing' | 'needs_update' | 'misconfigured';

export interface ComponentAuditItem {
  id: string;
  name: string;
  name_ar: string;
  status: ComponentAuditStatus;
  detected_version?: string;
  binary_path?: string;
  config_path?: string;
  why_needed: string;
  why_needed_ar: string;
  details: string;
  details_ar: string;
  action: string;
  action_ar: string;
  canInstall?: boolean;
}

export interface FullInfrastructureSnapshot {
  id: string;
  timestamp: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  items_count: number;
  included: string[];
  verified: boolean;
  type: 'full_infrastructure' | 'pre_install_guard';
}

export interface TraefikPortAudit {
  port: number;
  service_name: string;
  is_in_use: boolean;
  bound_address?: string;
  has_conflict: boolean;
}

export interface TraefikConnectedContainer {
  id: string;
  name: string;
  ipv4_address: string;
  status: string;
  ports: string[];
}

export interface TraefikSnapshot {
  id: string;
  timestamp: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  has_compose: boolean;
  has_acme: boolean;
  status: 'verified' | 'unverified';
}

export interface TraefikModuleConfig {
  config_dir: string;
  image: string;
  container_name: string;
  network: string;
  http_port: number;
  dashboard_external_port: number;
  dashboard_internal_port: number;
  odoo19_port: number;
  jenkins_port: number;
  dashboard_url: string;
  insecure_dashboard: boolean;
  enable_letsencrypt: boolean;
  dashboard_domain: string;
  acme_email: string;
  docker_socket_ro: boolean;
  basic_auth_user: string;
}

export interface TraefikDiscoveryData {
  timestamp: string;
  docker_installed: boolean;
  docker_version: string;
  compose_installed: boolean;
  compose_version: string;
  container_exists: boolean;
  container_status: 'running' | 'stopped' | 'not_found' | 'error';
  container_image: string;
  container_uptime: string;
  proxy_network_exists: boolean;
  proxy_subnet: string;
  connected_containers: TraefikConnectedContainer[];
  compose_file_exists: boolean;
  compose_file_path: string;
  dashboard_accessible: boolean;
  dashboard_url: string;
  acme_file_exists: boolean;
  acme_permissions_valid: boolean;
  ports_audit: TraefikPortAudit[];
  warnings: string[];
}

export interface OdooInstanceStatus {
  container_status: 'running' | 'stopped' | 'not_found' | 'error';
  image: string;
  uptime: string;
  db_ready: boolean;
  http_ready: boolean;
  version: string;
  pg_version: string;
}

export interface OdooDiscoveryData {
  timestamp: string;
  odoo17: OdooInstanceStatus;
  odoo18: OdooInstanceStatus;
  odoo19: OdooInstanceStatus;
  proxy_network_exists: boolean;
  warnings: string[];
}

export interface OdooSnapshot {
  id: string;
  version: '17' | '18' | '19';
  timestamp: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  status: 'verified' | 'unverified';
}

export interface OdooModuleConfig {
  dir_17: string;
  dir_19: string;
  image_17: string;
  image_19: string;
  pg_16_image: string;
  pg_18_image: string;
  internal_port: number;
  external_port_17: number;
  external_port_19: number;
  longpolling_port_17: number;
  longpolling_port_19: number;
}
