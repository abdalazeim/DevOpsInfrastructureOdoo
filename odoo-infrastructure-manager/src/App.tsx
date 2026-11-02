import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { TopologyView } from './components/TopologyView';
import { OperationsMenu } from './components/OperationsMenu';
import { ActiveWorkflowRunner } from './components/ActiveWorkflowRunner';
import { TerminalConsole } from './components/TerminalConsole';
import { ProfileEditorModal } from './components/ProfileEditorModal';
import { DatabaseManagerModal } from './components/DatabaseManagerModal';
import { ArchitectureFilesModal } from './components/ArchitectureFilesModal';
import { SystemOverviewBanner } from './components/SystemOverviewBanner';
import { PreflightCheckModal } from './components/PreflightCheckModal';
import { TraefikManagerModal } from './components/TraefikManagerModal';
import { OdooManagerModal } from './components/OdooManagerModal';
import { 
  DEFAULT_PROFILES, INITIAL_BACKUPS, INITIAL_CONTAINERS, 
  INITIAL_AUDIT_COMPONENTS, INITIAL_INFRASTRUCTURE_SNAPSHOTS,
  DEFAULT_TRAEFIK_MODULE_CONFIG, INITIAL_TRAEFIK_DISCOVERY, INITIAL_TRAEFIK_SNAPSHOTS
} from './data/defaultProfiles';
import { 
  InfrastructureProfile, Language, OperationPlan, 
  BackupMetadata, ContainerRuntimeHealth, ComponentAuditItem, FullInfrastructureSnapshot,
  TraefikDiscoveryData, TraefikModuleConfig, TraefikSnapshot, 
  OdooDiscoveryData, OdooInstanceStatus, OperationCategory
} from './types';
import { createOperationPlan } from './services/infrastructureSimulator';

export default function App() {
  const [lang, setLang] = useState<Language>('ar');
  const [profiles, setProfiles] = useState<InfrastructureProfile[]>(DEFAULT_PROFILES);
  const [currentProfile, setCurrentProfile] = useState<InfrastructureProfile>(DEFAULT_PROFILES[0]);
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [containers, setContainers] = useState<ContainerRuntimeHealth[]>(INITIAL_CONTAINERS);
  const [backups, setBackups] = useState<BackupMetadata[]>(INITIAL_BACKUPS);
  const [auditComponents, setAuditComponents] = useState<ComponentAuditItem[]>(INITIAL_AUDIT_COMPONENTS);
  const [infrastructureSnapshots, setInfrastructureSnapshots] = useState<FullInfrastructureSnapshot[]>(INITIAL_INFRASTRUCTURE_SNAPSHOTS);
  
  // Odoo Module State
  const [showOdooModal, setShowOdooModal] = useState<boolean>(false);
  const [odooDiscovery, setOdooDiscovery] = useState<OdooDiscoveryData>({
    timestamp: new Date().toISOString(),
    odoo17: { container_status: 'running', image: 'odoo:17.0', uptime: '14h', db_ready: true, http_ready: true, version: '17', pg_version: '16' },
    odoo19: { container_status: 'running', image: 'odoo:19.0', uptime: '14h', db_ready: true, http_ready: true, version: '19', pg_version: '18' },
    proxy_network_exists: true,
    warnings: []
  });

  // Traefik State
  const [showTraefikModal, setShowTraefikModal] = useState<boolean>(false);
  const [traefikDiscovery, setTraefikDiscovery] = useState<TraefikDiscoveryData>(INITIAL_TRAEFIK_DISCOVERY);
  const [traefikConfig, setTraefikConfig] = useState<TraefikModuleConfig>(DEFAULT_TRAEFIK_MODULE_CONFIG);
  const [traefikSnapshots, setTraefikSnapshots] = useState<TraefikSnapshot[]>(INITIAL_TRAEFIK_SNAPSHOTS);

  // Terminal & Execution State
  const [logs, setLogs] = useState<string[]>([
    '# ==============================================================================',
    '# Odoo Infrastructure Manager - Terminal Session Initialized',
    '# ==============================================================================',
  ]);

  const [activePlan, setActivePlan] = useState<OperationPlan | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Modals
  const [showProfileEditor, setShowProfileEditor] = useState<boolean>(false);
  const [showDatabaseManager, setShowDatabaseManager] = useState<boolean>(false);
  const [showFilesModal, setShowFilesModal] = useState<boolean>(false);
  const [showPreflightModal, setShowPreflightModal] = useState<boolean>(false);

  // Timer Ref
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isRunning && !isPaused) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => +(prev + 0.1).toFixed(1));
      }, 100);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning, isPaused]);

  const appendLog = (line: string) => {
    setLogs((prev) => [...prev, line]);
  };

  const handleLaunchOperation = (
    category: OperationCategory,
    extraParams?: { version?: '17' | '19'; dbName?: string; dumpFile?: string }
  ) => {
    if (isRunning) return;

    const plan = createOperationPlan(category, currentProfile, extraParams);
    plan.dryRun = dryRun;
    setActivePlan(plan);
    setCurrentStepIndex(0);
    setIsRunning(true);
    setIsPaused(false);
    setElapsedSeconds(0);

    appendLog(`\n==============================================================================`);
    appendLog(`>>> STARTING OPERATION: ${plan.name} (Dry-Run: ${dryRun ? 'TRUE' : 'FALSE'})`);
    appendLog(`>>> Category: ${plan.category} | Steps: ${plan.steps.length}`);
    appendLog(`==============================================================================\n`);

    executeWorkflowStep(plan, 0, dryRun);
  };

  const executeWorkflowStep = (plan: OperationPlan, stepIndex: number, isDryRun: boolean) => {
    if (stepIndex >= plan.steps.length) {
      setIsRunning(false);
      appendLog(`\n[OK] OPERATION COMPLETED SUCCESSFULLY: ${plan.name}`);
      appendLog(`[OK] All ${plan.steps.length} stages passed verification!\n`);
      return;
    }

    const currentStep = plan.steps[stepIndex];
    currentStep.status = 'running';
    setCurrentStepIndex(stepIndex);

    appendLog(`==> [${stepIndex + 1}/${plan.steps.length}] ${currentStep.name}`);
    
    const stepDuration = isDryRun ? 500 : 1500;

    setTimeout(() => {
      appendLog(`    [OK] ${currentStep.id} passed with exit code 0.`);
      currentStep.status = 'success';
      currentStep.duration = +(stepDuration / 1000).toFixed(1);
      appendLog(`[OK] Step '${currentStep.name}' completed in ${currentStep.duration}s\n`);
      executeWorkflowStep(plan, stepIndex + 1, isDryRun);
    }, stepDuration);
  };

  const handleOdooAction = (version: '17' | '19', action: 'start' | 'stop' | 'restart') => {
    appendLog(`[INFO] Odoo ${version} ${action} requested...`);
    handleLaunchOperation(version === '17' ? 'odoo17' : 'odoo19');
  };

  const handleTakeBackup = (version: '17' | '19', dbName: string) => {
    handleLaunchOperation('backup', { version, dbName });
  };

  const handleTriggerRestore = (version: '17' | '19', dumpFile: string, targetDb: string) => {
    handleLaunchOperation('restore', { version, dbName: targetDb, dumpFile });
  };

  const handleRefreshInspection = () => {
    appendLog(`\n[INFO] Running live pre-flight environment inspection...`);
    appendLog(`[INFO] Probing Ubuntu kernel, Docker socket, Compose plugins, Traefik, Ansible, and utilities...`);
    setTimeout(() => {
      appendLog(`[OK] Pre-flight audit sweep completed: 10/10 components inspected.`);
      appendLog(`[OK] All core components are healthy and verified.`);
    }, 600);
  };

  const handleCreateFullSnapshot = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const newSnapshot: FullInfrastructureSnapshot = {
      id: `snap-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      filename: `full_snapshot_${timestamp}.tar.gz`,
      size_bytes: 72400190,
      sha256: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      items_count: 145,
      included: [
        '.env (Environment Secrets)',
        'profiles/*.yaml (Configurations)',
        'deployment/traefik/ (Compose & SSL Certificates)',
        'deployment/odoo17/ (Compose & Config)',
        'deployment/odoo19/ (Compose & Config)',
        'automation/ansible/ (Playbooks)',
        'PostgreSQL Logical Dumps',
      ],
      verified: true,
      type: 'full_infrastructure',
    };
    setInfrastructureSnapshots((prev) => [newSnapshot, ...prev]);
    appendLog(`\n[OK] Full Infrastructure Snapshot generated: ${newSnapshot.filename}`);
    appendLog(`[OK] SHA256: ${newSnapshot.sha256}`);
    appendLog(`[OK] Saved to: /opt/odoo-infrastructure/backups/system_snapshots/\n`);
  };

  const handleInstallSelected = (componentIds: string[], createBackupFirst: boolean) => {
    appendLog(`\n==============================================================================`);
    appendLog(`>>> SMART AUTO-INSTALLER TRIGGERED`);
    appendLog(`>>> Selected Components: ${componentIds.join(', ')}`);
    appendLog(`==============================================================================\n`);

    if (createBackupFirst) {
      appendLog(`[INFO] Creating pre-installation safety infrastructure snapshot...`);
      handleCreateFullSnapshot();
    }

    appendLog(`[INFO] Launching non-destructive package installation...`);
    setAuditComponents((prev) =>
      prev.map((c) =>
        componentIds.includes(c.id)
          ? { ...c, status: 'installed', action: 'Installed via Smart Installer', action_ar: 'تم التثبيت بنجاح' }
          : c
      )
    );
    appendLog(`[OK] All selected components have been safely provisioned without modifying existing packages!\n`);
  };

  const handleRestoreFullSnapshot = (snapshotId: string) => {
    const target = infrastructureSnapshots.find((s) => s.id === snapshotId);
    appendLog(`\n[WARN] Starting verified full infrastructure restore: ${target?.filename || snapshotId}`);
    appendLog(`[INFO] Automatic safety snapshot generated in safety_pre_restore/`);
    appendLog(`[OK] Configurations, environments, and databases restored successfully!\n`);
  };

  const handleRefreshTraefikDiscovery = () => {
    appendLog(`\n[INFO] Discovering Traefik v3.7 Docker environment...`);
    appendLog(`[INFO] Checking container status, 'proxy' network IPAM, ports (80, 10090, 8080, 10019, 8081), and acme.json...`);
    setTimeout(() => {
      setTraefikDiscovery((prev) => ({
        ...prev,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        dashboard_accessible: true,
      }));
      appendLog(`[OK] Traefik environment discovery completed: Container is RUNNING, proxy network is healthy.`);
      appendLog(`[OK] Dashboard accessible at http://localhost:10090/dashboard/ (Port 80 bound)`);
    }, 600);
  };

  const handleDeployTraefikModule = (newConfig: TraefikModuleConfig) => {
    appendLog(`\n[INFO] Starting safe Traefik deployment to ${newConfig.config_dir}...`);
    appendLog(`[INFO] Creating pre-change backup in ${newConfig.config_dir}/backups/...`);
    handleCreateTraefikSnapshot();

    appendLog(`[INFO] Validating docker-compose.yml configuration with 'docker compose config'...`);
    appendLog(`[OK] Configuration valid! Read-only socket (/var/run/docker.sock:ro) confirmed.`);

    handleLaunchOperation('traefik');
  };

  const handleRestartTraefikContainer = () => {
    appendLog(`[INFO] Restarting Traefik container (docker restart traefik)...`);
    setTimeout(() => {
      appendLog(`[OK] Traefik container restarted successfully with zero disruption to Odoo services.\n`);
    }, 800);
  };

  const handleStopTraefikContainer = () => {
    appendLog(`[WARN] Stopping Traefik container (docker stop traefik) - volumes and proxy network preserved...`);
    setTraefikDiscovery((prev) => ({
      ...prev,
      container_status: 'stopped',
      dashboard_accessible: false,
    }));
    appendLog(`[OK] Traefik container stopped safely.\n`);
  };

  const handleStartTraefikContainer = () => {
    appendLog(`[INFO] Starting Traefik container (docker start traefik)...`);
    setTraefikDiscovery((prev) => ({
      ...prev,
      container_status: 'running',
      dashboard_accessible: true,
    }));
    appendLog(`[OK] Traefik container is now running.\n`);
  };

  const handleCreateTraefikSnapshot = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const newSnap: TraefikSnapshot = {
      id: `snap-trf-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      filename: `traefik_backup_${timestamp}.tar.gz`,
      size_bytes: 42350,
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      has_compose: true,
      has_acme: true,
      status: 'verified',
    };
    setTraefikSnapshots((prev) => [newSnap, ...prev]);
    appendLog(`[OK] Traefik snapshot created: ${newSnap.filename} (SHA256 verified, chmod 600)`);
  };

  const handleRestoreTraefikSnapshot = (snapshotId: string) => {
    const target = traefikSnapshots.find((s) => s.id === snapshotId);
    appendLog(`\n[WARN] Restoring Traefik backup: ${target?.filename || snapshotId}`);
    appendLog(`[INFO] Automated pre-restore rollback snapshot generated in /opt/traefik/backups/safety_rollback/`);
    appendLog(`[OK] docker-compose.yml and acme.json restored successfully with 0600 permissions!\n`);
  };

  const handleConnectContainerToProxy = (cname: string) => {
    appendLog(`[INFO] docker network connect proxy ${cname}...`);
    setTraefikDiscovery((prev) => ({
      ...prev,
      connected_containers: [
        ...prev.connected_containers,
        {
          id: `c-${Date.now().toString().slice(-6)}`,
          name: cname,
          ipv4_address: `172.28.0.${prev.connected_containers.length + 2}`,
          status: 'Attached',
          ports: ['Internal / Proxy'],
        },
      ],
    }));
    appendLog(`[OK] Container '${cname}' attached to proxy network successfully.\n`);
  };

  const handleDisconnectContainerFromProxy = (cname: string) => {
    appendLog(`[INFO] docker network disconnect proxy ${cname}...`);
    setTraefikDiscovery((prev) => ({
      ...prev,
      connected_containers: prev.connected_containers.filter((c) => c.name !== cname),
    }));
    appendLog(`[OK] Container '${cname}' disconnected from proxy network safely.\n`);
  };

  const handleTestTraefikConnectivity = () => {
    appendLog(`\n[INFO] Running Traefik routing and connectivity probe...`);
    appendLog(`[INFO] Testing TCP socket on 127.0.0.1:80 (HTTP Entrypoint)...`);
    appendLog(`[INFO] Testing TCP socket on 127.0.0.1:10090 (Dashboard Management)...`);
    setTimeout(() => {
      appendLog(`[OK] Port 80 is listening and redirecting HTTP traffic.`);
      appendLog(`[OK] Dashboard at http://localhost:10090/dashboard/ responded with HTTP 200 OK.`);
      appendLog(`[OK] Network 'proxy' routing verified for Odoo 17, Odoo 19, and Jenkins.\n`);
    }, 500);
  };

  const activeContainersCount = containers.filter((c) => c.status === 'running').length;

  return (
    <div
      dir={lang === 'ar' ? 'rtl' : 'ltr'}
      className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-900 selection:text-cyan-100"
    >
      <Header
        currentProfile={currentProfile}
        profiles={profiles}
        onSelectProfile={(p) => {
          setCurrentProfile(p);
          appendLog(`[INFO] Switched active profile to: ${p.profile_name} (Host: ${p.server.hostname})`);
        }}
        lang={lang}
        onToggleLang={() => setLang(lang === 'ar' ? 'en' : 'ar')}
        dryRun={dryRun}
        onToggleDryRun={() => {
          setDryRun(!dryRun);
          appendLog(`[INFO] Dry-run simulation mode is now: ${!dryRun ? 'ENABLED' : 'DISABLED'}`);
        }}
        onOpenProfileEditor={() => setShowProfileEditor(true)}
        onOpenFilesModal={() => setShowFilesModal(true)}
        onOpenPreflightModal={() => setShowPreflightModal(true)}
        onOpenTraefikModal={() => setShowTraefikModal(true)}
        activeContainersCount={activeContainersCount}
      />

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 space-y-6">
        
        <SystemOverviewBanner lang={lang} />

        {activePlan && (
          <ActiveWorkflowRunner
            plan={activePlan}
            currentStepIndex={currentStepIndex}
            isRunning={isRunning}
            isPaused={isPaused}
            elapsedSeconds={elapsedSeconds}
            lang={lang}
            onPauseResume={() => setIsPaused(!isPaused)}
            onCancel={() => {
              setIsRunning(false);
              appendLog(`[WARN] Operation cancelled by operator!`);
            }}
            onClose={() => setActivePlan(null)}
          />
        )}

        <TopologyView
          profile={currentProfile}
          containers={containers}
          lang={lang}
          onSelectService={(svc) => {
            appendLog(`[INFO] Querying recent logs and status for container: ${svc}...`);
            appendLog(`[OK] Container ${svc} is healthy. Uptime: up 4 days.`);
          }}
        />

        <OperationsMenu
          lang={lang}
          onLaunchOperation={(cat) => handleLaunchOperation(cat)}
          onOpenDatabaseManager={() => setShowDatabaseManager(true)}
          onOpenPreflight={() => setShowPreflightModal(true)}
          onOpenTraefikManager={() => setShowTraefikModal(true)}
          onOpenOdooManager={() => setShowOdooModal(true)}
          onOpenProfileEditor={() => setShowProfileEditor(true)}
          isOperationRunning={isRunning}
        />

        <TerminalConsole
          logs={logs}
          lang={lang}
          onClearLogs={() => setLogs([])}
          hostname={currentProfile.server.hostname}
        />

      </main>

      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Odoo Infrastructure Manager • Ubuntu Server • Traefik v3.7 • PostgreSQL 16 & 18</span>
          <span>Docker Engine & Compose v2 • Ansible Automation</span>
        </div>
      </footer>

      {showOdooModal && (
        <OdooManagerModal
          isOpen={showOdooModal}
          onClose={() => setShowOdooModal(false)}
          lang={lang}
          discovery={odooDiscovery}
          onRefreshDiscovery={() => {
            appendLog('[INFO] Refreshing Odoo environment status...');
            appendLog('[OK] Odoo 17 & 19 services are running normally.');
          }}
          onAction={handleOdooAction}
          isOperationRunning={isRunning}
        />
      )}

      {showTraefikModal && (
        <TraefikManagerModal
          isOpen={showTraefikModal}
          onClose={() => setShowTraefikModal(false)}
          lang={lang}
          discovery={traefikDiscovery}
          config={traefikConfig}
          snapshots={traefikSnapshots}
          onRefreshDiscovery={handleRefreshTraefikDiscovery}
          onUpdateConfig={(cfg) => {
            setTraefikConfig(cfg);
            appendLog(`[OK] Traefik module configuration updated.`);
          }}
          onDeployTraefik={handleDeployTraefikModule}
          onRestartContainer={handleRestartTraefikContainer}
          onStopContainer={handleStopTraefikContainer}
          onStartContainer={handleStartTraefikContainer}
          onCreateSnapshot={handleCreateTraefikSnapshot}
          onRestoreSnapshot={handleRestoreTraefikSnapshot}
          onConnectContainerToProxy={handleConnectContainerToProxy}
          onDisconnectContainerFromProxy={handleDisconnectContainerFromProxy}
          onTestConnectivity={handleTestTraefikConnectivity}
          isOperationRunning={isRunning}
        />
      )}

      {showProfileEditor && (
        <ProfileEditorModal
          profile={currentProfile}
          lang={lang}
          onSave={(updated) => {
            setCurrentProfile(updated);
            setProfiles(profiles.map((p) => (p.profile_name === updated.profile_name ? updated : p)));
            appendLog(`[OK] Updated profile '${updated.profile_name}' applied successfully.`);
          }}
          onClose={() => setShowProfileEditor(false)}
        />
      )}

      {showDatabaseManager && (
        <DatabaseManagerModal
          profile={currentProfile}
          backups={backups}
          lang={lang}
          onTakeBackup={handleTakeBackup}
          onTriggerRestore={handleTriggerRestore}
          onClose={() => setShowDatabaseManager(false)}
        />
      )}

      {showFilesModal && (
        <ArchitectureFilesModal
          lang={lang}
          onClose={() => setShowFilesModal(false)}
        />
      )}

      {showPreflightModal && (
        <PreflightCheckModal
          components={auditComponents}
          snapshots={infrastructureSnapshots}
          lang={lang}
          onRefreshInspection={handleRefreshInspection}
          onInstallSelected={handleInstallSelected}
          onCreateSnapshot={handleCreateFullSnapshot}
          onRestoreSnapshot={handleRestoreFullSnapshot}
          onClose={() => setShowPreflightModal(false)}
        />
      )}
    </div>
  );
}
