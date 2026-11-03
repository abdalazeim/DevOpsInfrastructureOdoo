import {
  BackupMetadata,
  ComponentAuditItem,
  ContainerRuntimeHealth,
  FullInfrastructureSnapshot,
  InfrastructureProfile,
  OdooDiscoveryData,
  TraefikDiscoveryData,
  TraefikSnapshot,
} from '../types';

/**
 * Thin client for the local Python API (app/api_server.py).
 *
 * In development Vite proxies /api to http://127.0.0.1:8787 (see vite.config.ts).
 * Production can point VITE_API_BASE at another origin.
 */
const API_BASE: string =
  ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE) || '/api';

export const API_AVAILABLE_EVENT = 'odoo-api-availability';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`API ${path} failed with HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function isApiAvailable(): Promise<boolean> {
  try {
    const health = await request<{ status: string }>('/health');
    return health.status === 'ok';
  } catch {
    return false;
  }
}

export function fetchProfiles(): Promise<InfrastructureProfile[]> {
  return request<InfrastructureProfile[]>('/profiles');
}

interface RawPreflightComponent {
  id: string;
  name: string;
  name_ar: string;
  status: string;
  detected_version?: string;
  binary_path?: string;
  config_path?: string;
  why_needed?: string;
  why_needed_ar?: string;
  details?: string;
  details_ar?: string;
  recommended_action?: string;
  recommended_action_ar?: string;
  install_command?: string[];
}

interface RawPreflightReport {
  components: RawPreflightComponent[];
}

function mapStatus(status: string): ComponentAuditItem['status'] {
  switch (status.toUpperCase()) {
    case 'INSTALLED':
      return 'installed';
    case 'NEEDS_UPDATE':
      return 'needs_update';
    case 'MISCONFIGURED':
      return 'misconfigured';
    default:
      return 'missing';
  }
}

export async function fetchPreflightAudit(): Promise<ComponentAuditItem[]> {
  const report = await request<RawPreflightReport>('/preflight');
  return (report.components || []).map((component) => ({
    id: component.id,
    name: component.name,
    name_ar: component.name_ar,
    status: mapStatus(component.status),
    detected_version: component.detected_version,
    binary_path: component.binary_path,
    config_path: component.config_path,
    why_needed: component.why_needed || '',
    why_needed_ar: component.why_needed_ar || '',
    details: component.details || '',
    details_ar: component.details_ar || '',
    action: component.recommended_action || '',
    action_ar: component.recommended_action_ar || '',
    canInstall: !!component.install_command,
  }));
}

export function fetchTraefikDiscovery(): Promise<TraefikDiscoveryData> {
  return request<TraefikDiscoveryData>('/traefik/discovery');
}

export function fetchTraefikSnapshots(): Promise<TraefikSnapshot[]> {
  return request<TraefikSnapshot[]>('/traefik/snapshots');
}

export function fetchOdooDiscovery(): Promise<OdooDiscoveryData> {
  return request<OdooDiscoveryData>('/odoo/discovery');
}

interface RawDockerContainer {
  ID?: string;
  Names?: string;
  Image?: string;
  Status?: string;
  State?: string;
  Ports?: string;
  Networks?: string;
}

function mapDockerStatus(state: string): ContainerRuntimeHealth['status'] {
  const normalized = (state || '').toLowerCase();
  if (normalized === 'running') return 'running';
  if (normalized === 'restarting') return 'restarting';
  if (normalized === 'exited' || normalized === 'dead') return 'exited';
  return 'not_deployed';
}

export async function fetchContainers(): Promise<ContainerRuntimeHealth[]> {
  const raw = await request<RawDockerContainer[]>('/containers');
  return raw.map((container) => {
    const name = container.Names || container.ID?.slice(0, 12) || 'unknown';
    return {
      name,
      service: name,
      status: mapDockerStatus(container.State || ''),
      healthcheck: 'none',
      image: container.Image || 'unknown',
      ports: (container.Ports || '').split(',').map((port) => port.trim()).filter(Boolean),
      uptime: container.Status || 'N/A',
      cpu_percent: 0,
      memory_mb: 0,
      network: (container.Networks || '').split(',').map((net) => net.trim()).filter(Boolean),
    };
  });
}

export function fetchBackups(): Promise<BackupMetadata[]> {
  return request<BackupMetadata[]>('/backups');
}

export function fetchSnapshots(): Promise<FullInfrastructureSnapshot[]> {
  return request<FullInfrastructureSnapshot[]>('/snapshots');
}

export interface LaunchOperationPayload {
  category: string;
  version?: '17' | '18' | '19';
  dbName?: string;
  dumpFile?: string;
  dryRun?: boolean;
  execute?: boolean;
}

export interface ApiOperationRecord {
  id: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  operation: {
    name: string;
    steps: Array<{
      id: string;
      name: string;
      status: string;
      stdout?: string;
      stderr?: string;
      exit_code?: number | null;
    }>;
  };
}

export function launchOperation(payload: LaunchOperationPayload): Promise<ApiOperationRecord> {
  return request<ApiOperationRecord>('/operations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchOperation(id: string): Promise<ApiOperationRecord> {
  return request<ApiOperationRecord>(`/operations/${id}`);
}
