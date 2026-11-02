import React, { useState } from 'react';
import { 
  X, Shield, Server, Network, Layers, RefreshCw, 
  Play, Square, RotateCcw, Copy, Check, ExternalLink, 
  AlertTriangle, Lock, Unlock, FileText, CheckCircle2, Download
} from 'lucide-react';
import { 
  Language, TraefikDiscoveryData, TraefikModuleConfig, 
  TraefikSnapshot, TraefikPortAudit, TraefikConnectedContainer 
} from '../types';

interface TraefikManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang: Language;
  discovery: TraefikDiscoveryData;
  config: TraefikModuleConfig;
  snapshots: TraefikSnapshot[];
  onRefreshDiscovery: () => void;
  onUpdateConfig: (newConfig: TraefikModuleConfig) => void;
  onDeployTraefik: (config: TraefikModuleConfig) => void;
  onRestartContainer: () => void;
  onStopContainer: () => void;
  onStartContainer: () => void;
  onCreateSnapshot: () => void;
  onRestoreSnapshot: (snapshotId: string) => void;
  onConnectContainerToProxy: (containerName: string) => void;
  onDisconnectContainerFromProxy: (containerName: string) => void;
  onTestConnectivity: () => void;
  isOperationRunning: boolean;
}

export const TraefikManagerModal: React.FC<TraefikManagerModalProps> = ({
  isOpen,
  onClose,
  lang,
  discovery,
  config,
  snapshots,
  onRefreshDiscovery,
  onUpdateConfig,
  onDeployTraefik,
  onRestartContainer,
  onStopContainer,
  onStartContainer,
  onCreateSnapshot,
  onRestoreSnapshot,
  onConnectContainerToProxy,
  onDisconnectContainerFromProxy,
  onTestConnectivity,
  isOperationRunning,
}) => {
  if (!isOpen) return null;

  const isAr = lang === 'ar';
  const [activeTab, setActiveTab] = useState<'discovery' | 'network' | 'labels' | 'compose' | 'backups' | 'logs'>('discovery');
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [restoreConfirmText, setRestoreConfirmText] = useState<string>('');
  const [newContainerToConnect, setNewContainerToConnect] = useState<string>('');

  // Local config form state
  const [localConfig, setLocalConfig] = useState<TraefikModuleConfig>(config);

  // Label generator state
  const [labelService, setLabelService] = useState<'odoo17' | 'odoo19' | 'jenkins' | 'custom'>('odoo19');
  const [labelDomain, setLabelDomain] = useState<string>('odoo19.devops-odoo.internal');
  const [labelPort, setLabelPort] = useState<number>(10019);
  const [labelPathPrefix, setLabelPathPrefix] = useState<string>('');
  const [labelEnableTls, setLabelEnableTls] = useState<boolean>(false);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const getGeneratedLabels = () => {
    const labels = [
      '# Docker Compose Labels for Traefik Ingress',
      'labels:',
      '  - "traefik.enable=true"',
      `  - "traefik.http.routers.${labelService}.rule=Host(\`${labelDomain}\`)"`,
      `  - "traefik.http.routers.${labelService}.entrypoints=${labelEnableTls ? 'websecure' : 'web'}"`,
      `  - "traefik.http.services.${labelService}.loadbalancer.server.port=${labelPort}"`,
    ];

    if (labelPathPrefix) {
      labels.push(`  - "traefik.http.middlewares.${labelService}-prefix.stripprefix.prefixes=${labelPathPrefix}"`);
      labels.push(`  - "traefik.http.routers.${labelService}.middlewares=${labelService}-prefix"`);
    }

    if (labelEnableTls) {
      labels.push(`  - "traefik.http.routers.${labelService}.tls=true"`);
      labels.push(`  - "traefik.http.routers.${labelService}.tls.certresolver=letsencrypt"`);
    }

    if (labelService.includes('odoo')) {
      labels.push(`  # Dedicated Odoo Livechat WebSocket router on port 8072`);
      labels.push(`  - "traefik.http.routers.${labelService}-chat.rule=Host(\`${labelDomain}\`) && PathPrefix(\`/websocket\`)"`);
      labels.push(`  - "traefik.http.routers.${labelService}-chat.entrypoints=${labelEnableTls ? 'websecure' : 'web'}"`);
      labels.push(`  - "traefik.http.routers.${labelService}-chat.service=${labelService}-chat"`);
      labels.push(`  - "traefik.http.services.${labelService}-chat.loadbalancer.server.port=8072"`);
    }

    return labels.join('\n');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden"
        dir={isAr ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 p-0.5 flex items-center justify-center shadow-lg shadow-cyan-950/40">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Shield className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">
                  {isAr ? 'وحدة إدارة Traefik على Docker (Ubuntu)' : 'Traefik Docker Management Module (Ubuntu)'}
                </h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                  traefik:v3.7
                </span>
              </div>
              <p className="text-xs text-slate-400">
                {isAr 
                  ? 'إدارة متكاملة للموجه، شبكة proxy الخارجية، المنافذ 80 و 10090، وتوجيه Odoo 17 و 19 و Jenkins' 
                  : 'Full orchestrator for Traefik v3.7, external proxy network, ports 80 & 10090, Odoo 17, 19 & Jenkins'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onRefreshDiscovery}
              title={isAr ? 'إعادة الفحص المسبق والاكتشاف' : 'Refresh environment discovery'}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 px-6 pt-3 border-b border-slate-800 bg-slate-900/40 overflow-x-auto text-xs shrink-0">
          <button
            onClick={() => setActiveTab('discovery')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'discovery'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>{isAr ? 'الفحص والاكتشاف والمنافذ' : 'Discovery & Port Matrix'}</span>
          </button>

          <button
            onClick={() => setActiveTab('network')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'network'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>{isAr ? 'شبكة proxy والحاويات' : 'Proxy Network & Services'}</span>
          </button>

          <button
            onClick={() => setActiveTab('labels')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'labels'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{isAr ? 'منشئ Docker Labels' : 'Docker Labels Builder'}</span>
          </button>

          <button
            onClick={() => setActiveTab('compose')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'compose'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{isAr ? 'ملف Compose والأمان' : 'Compose & Security'}</span>
          </button>

          <button
            onClick={() => setActiveTab('backups')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'backups'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>{isAr ? 'النسخ والاستعادة' : 'Backups & Snapshots'}</span>
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3.5 py-2 font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'logs'
                ? 'bg-slate-800 text-cyan-300 border-t-2 border-cyan-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{isAr ? 'التحكم بالسجلات والاختبار' : 'Control & Logs'}</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* TAB 1: DISCOVERY & PORT MATRIX */}
          {activeTab === 'discovery' && (
            <div className="space-y-6">
              {/* Status Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl p-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>{isAr ? 'حاوية Traefik' : 'Traefik Container'}</span>
                    <Server className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${discovery.container_status === 'running' ? 'bg-emerald-400' : 'bg-rose-500'}`} />
                    <span className="capitalize">{discovery.container_status}</span>
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 mt-1">{discovery.container_image}</p>
                </div>

                <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl p-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>{isAr ? 'شبكة proxy الخارجية' : 'Proxy Network'}</span>
                    <Network className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-sm font-bold text-slate-100">
                    {discovery.proxy_network_exists ? (isAr ? 'متصلة وجاهزة' : 'Active & Bound') : (isAr ? 'غير منشأة' : 'Missing')}
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 mt-1">{discovery.proxy_subnet}</p>
                </div>

                <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl p-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>{isAr ? 'أذونات الشهادات' : 'ACME Permissions'}</span>
                    <Lock className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-sm font-bold text-slate-100">
                    {discovery.acme_permissions_valid ? (isAr ? 'صحيحة 0600' : 'Strict 0600') : (isAr ? 'غير آمنة' : 'Insecure')}
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 mt-1">/opt/traefik/acme/acme.json</p>
                </div>

                <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl p-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>{isAr ? 'رابط لوحة التحكم' : 'Dashboard Reachability'}</span>
                    <ExternalLink className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-sm font-bold text-slate-100">
                    {discovery.dashboard_accessible ? (isAr ? 'متاحة للوصول' : 'Listening 10090') : (isAr ? 'غير متصلة' : 'Offline')}
                  </div>
                  <p className="text-[11px] font-mono text-cyan-400 mt-1 truncate">
                    <a href={discovery.dashboard_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                      {discovery.dashboard_url}
                    </a>
                  </p>
                </div>
              </div>

              {/* Ports Audit Table */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">
                      {isAr ? 'مصفوفة فحص المنافذ واكتشاف التعارضات' : 'Port Allocation & Conflict Detection Matrix'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'التحقق التلقائي من خلو المنافذ وعدم تصادم Traefik مع خوادم أخرى' : 'Probes active listening sockets on Ubuntu host'}
                    </p>
                  </div>
                  <button
                    onClick={onTestConnectivity}
                    className="text-xs px-3 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 flex items-center gap-1.5 font-mono"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>{isAr ? 'إعادة فحص المنافذ' : 'Test Ports'}</span>
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-800/70 text-slate-400 uppercase text-[10px]">
                      <tr>
                        <th className="py-2.5 px-3">{isAr ? 'المنفذ' : 'Port'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'الخدمة المقصودة' : 'Service Role'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'الحالة الحالية' : 'Socket State'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'العنوان المقيد' : 'Bound Address'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'التعارض' : 'Conflict Risk'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/60 text-slate-300">
                      {discovery.ports_audit.map((pa) => (
                        <tr key={pa.port} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-bold text-cyan-300">:{pa.port}</td>
                          <td className="py-2.5 px-3 text-slate-200">{pa.service_name}</td>
                          <td className="py-2.5 px-3">
                            {pa.is_in_use ? (
                              <span className="text-emerald-400 font-semibold">{isAr ? 'مستمع / نشط' : 'BOUND / IN USE'}</span>
                            ) : (
                              <span className="text-slate-400">{isAr ? 'متاح / شاغر' : 'FREE'}</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{pa.bound_address || 'None'}</td>
                          <td className="py-2.5 px-3">
                            {pa.has_conflict ? (
                              <span className="text-rose-400 flex items-center gap-1 font-bold">
                                <AlertTriangle className="w-3 h-3" /> {isAr ? 'تعارض محتمل' : 'CONFLICT'}
                              </span>
                            ) : (
                              <span className="text-emerald-400 flex items-center gap-1">
                                <Check className="w-3 h-3" /> {isAr ? 'سليم' : 'NOMINAL'}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Dashboard Access Link & Security Advisory */}
              <div className="bg-slate-800/30 border border-slate-700/80 rounded-xl p-4 flex items-start gap-3">
                <div className="p-2 rounded-lg bg-amber-950/60 border border-amber-800/80 text-amber-400 shrink-0">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div className="text-xs space-y-1">
                  <h4 className="font-bold text-slate-200">
                    {isAr ? 'تنبيه أمان لوحة التحكم (Traefik Dashboard)' : 'Security Advisory for Traefik Dashboard'}
                  </h4>
                  <p className="text-slate-400 leading-relaxed">
                    {isAr
                      ? 'المنفذ 10090 وخيار api.insecure=true مخصصان للمعاينة والإدارة المحلية فقط. في بيئات الإنتاج، لا تقم بفتح المنفذ 10090 للعامة عبر الجدار الناري (Firewall)، واعتمد دائمًا على التوجيه المشفر مع كلمة مرور BasicAuth.'
                      : 'Port 10090 with api.insecure=true is strictly intended for local management. Never publish port 10090 to public internet or firewall without BasicAuth router authentication and SSL/TLS protection.'}
                  </p>
                  <div className="pt-2 flex items-center gap-3">
                    <a
                      href={discovery.dashboard_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold font-mono transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>{isAr ? 'فتح لوحة التحكم (10090)' : 'Open Traefik Dashboard'}</span>
                    </a>
                    <button
                      onClick={() => handleCopy(discovery.dashboard_url, 'dash_url')}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono transition-colors"
                    >
                      {copiedText === 'dash_url' ? (isAr ? 'تم النسخ!' : 'Copied!') : (isAr ? 'نسخ الرابط' : 'Copy URL')}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: PROXY NETWORK & SERVICES */}
          {activeTab === 'network' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <Network className="w-4 h-4 text-cyan-400" />
                    {isAr ? 'الخدمات المتصلة بشبكة proxy المشتركة' : 'Containers Attached to External Network "proxy"'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {isAr ? 'الشبكة المعزولة التي تتيح لـ Traefik توجيه الطلبات للحاويات (Subnet: 172.28.0.0/16)' : 'Dedicated bridge facilitating ingress routing without exposing internal database ports'}
                  </p>
                </div>
              </div>

              {/* Connect New Container Form */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 flex items-center gap-3">
                <input
                  type="text"
                  placeholder={isAr ? 'اسم الحاوية المراد ربطها (مثل: jenkins, odoo19)' : 'Container name to attach (e.g. jenkins, odoo19)'}
                  value={newContainerToConnect}
                  onChange={(e) => setNewContainerToConnect(e.target.value)}
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
                <button
                  disabled={!newContainerToConnect.trim() || isOperationRunning}
                  onClick={() => {
                    onConnectContainerToProxy(newContainerToConnect.trim());
                    setNewContainerToConnect('');
                  }}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs font-mono transition-all disabled:opacity-50"
                >
                  {isAr ? 'ربط بالشبكة' : 'Attach to proxy'}
                </button>
              </div>

              {/* Connected Containers Table */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-800/70 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="py-3 px-4">{isAr ? 'الحاوية' : 'Container'}</th>
                      <th className="py-3 px-4">{isAr ? 'معرف الحاوية' : 'Container ID'}</th>
                      <th className="py-3 px-4">{isAr ? 'عنوان IP على proxy' : 'IPv4 Address'}</th>
                      <th className="py-3 px-4">{isAr ? 'المنافذ والمسارات' : 'Published / Target Ports'}</th>
                      <th className="py-3 px-4 text-right">{isAr ? 'إجراء' : 'Action'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/60 text-slate-300">
                    {discovery.connected_containers.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-4 font-bold text-slate-100 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-400" />
                          <span>{c.name}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{c.id}</td>
                        <td className="py-3 px-4 text-cyan-300">{c.ipv4_address}</td>
                        <td className="py-3 px-4 text-slate-300">
                          {c.ports.join(', ') || 'Internal Only'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {c.name !== 'traefik' ? (
                            <button
                              onClick={() => onDisconnectContainerFromProxy(c.name)}
                              disabled={isOperationRunning}
                              className="text-[11px] px-2.5 py-1 rounded bg-rose-950/80 text-rose-300 hover:bg-rose-900 border border-rose-800 transition-colors"
                            >
                              {isAr ? 'فصل من proxy' : 'Detach'}
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-500 font-mono">{isAr ? 'البروكسي الرئيسي' : 'Ingress Host'}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: DOCKER LABEL BUILDER */}
          {activeTab === 'labels' && (
            <div className="space-y-6">
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-5 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">
                    {isAr ? 'منشئ ملصقات التوجيه لـ Traefik (Docker Labels Generator)' : 'Traefik Ingress Docker Labels Generator'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {isAr ? 'توليد ملصقات التوجيه التلقائي لخدمات Odoo 17 و Odoo 19 و Jenkins وغيرها' : 'Generates declarative Traefik labels for docker-compose.yml'}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'نوع الخدمة' : 'Service Type'}</label>
                    <select
                      value={labelService}
                      onChange={(e) => {
                        const val = e.target.value as any;
                        setLabelService(val);
                        if (val === 'odoo17') {
                          setLabelDomain('odoo17.devops-odoo.internal');
                          setLabelPort(8069);
                        } else if (val === 'odoo19') {
                          setLabelDomain('odoo19.devops-odoo.internal');
                          setLabelPort(10019);
                        } else if (val === 'jenkins') {
                          setLabelDomain('jenkins.devops-odoo.internal');
                          setLabelPort(8081);
                        }
                      }}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                    >
                      <option value="odoo17">Odoo 17 (Port 8069 & WS 8072)</option>
                      <option value="odoo19">Odoo 19 (Port 10019 & WS 8072)</option>
                      <option value="jenkins">Jenkins CI/CD (Port 8081)</option>
                      <option value="custom">Custom Container Service</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'النطاق المستهدف' : 'Router Domain'}</label>
                    <input
                      type="text"
                      value={labelDomain}
                      onChange={(e) => setLabelDomain(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'المنفذ الداخلي للحاوية' : 'Target Port'}</label>
                    <input
                      type="number"
                      value={labelPort}
                      onChange={(e) => setLabelPort(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'تشفير Let\'s Encrypt' : 'Enable ACME TLS'}</label>
                    <button
                      type="button"
                      onClick={() => setLabelEnableTls(!labelEnableTls)}
                      className={`w-full py-2 px-3 rounded-lg text-xs font-mono font-semibold transition-colors border ${
                        labelEnableTls
                          ? 'bg-emerald-950/80 border-emerald-600 text-emerald-300'
                          : 'bg-slate-900 border-slate-700 text-slate-400'
                      }`}
                    >
                      {labelEnableTls ? (isAr ? 'مفعّل (websecure 443)' : 'TLS Enabled') : (isAr ? 'معطل (web 80)' : 'HTTP (Port 80)')}
                    </button>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-400">{isAr ? 'معاينة الملصقات الناتجة' : 'Generated Docker Compose Syntax'}:</span>
                    <button
                      onClick={() => handleCopy(getGeneratedLabels(), 'labels_code')}
                      className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-mono flex items-center gap-1"
                    >
                      {copiedText === 'labels_code' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedText === 'labels_code' ? (isAr ? 'تم النسخ' : 'Copied') : (isAr ? 'نسخ الملصقات' : 'Copy Labels')}</span>
                    </button>
                  </div>
                  <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-cyan-300 font-mono text-xs overflow-x-auto leading-relaxed">
                    {getGeneratedLabels()}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: COMPOSE & SECURITY CONFIGURATION */}
          {activeTab === 'compose' && (
            <div className="space-y-6">
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">
                      {isAr ? 'إعدادات Traefik و Docker Compose في /opt/traefik' : 'Traefik Compose Configuration (/opt/traefik/docker-compose.yml)'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'تخصيص المنافذ وسياسات أمان لوحة التحكم ومسار Docker Socket' : 'Configures ports, dashboard exposure mode, and permissions'}
                    </p>
                  </div>
                </div>

                {/* Dashboard Mode Selection */}
                <div className="p-4 rounded-xl border border-slate-700 bg-slate-900/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        {localConfig.insecure_dashboard ? <Unlock className="w-4 h-4 text-amber-400" /> : <Lock className="w-4 h-4 text-emerald-400" />}
                        <span>{isAr ? 'وضع لوحة التحكم (Dashboard Mode)' : 'Dashboard Exposure Mode'}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {localConfig.insecure_dashboard 
                          ? (isAr ? 'الوضع المحلي التجريبي: نشر المنفذ 10090:8080 بدون مصادقة' : 'Local Dev: Publishes 10090:8080 with api.insecure=true')
                          : (isAr ? 'وضع الإنتاج الآمن: التوجيه عبر Router مع كلمة مرور ومصادقة مشفرة' : 'Secure Production: Protected via Traefik Router with BasicAuth')}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => setLocalConfig({ ...localConfig, insecure_dashboard: !localConfig.insecure_dashboard })}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all border ${
                        localConfig.insecure_dashboard
                          ? 'bg-amber-950/80 border-amber-600 text-amber-300'
                          : 'bg-emerald-950/80 border-emerald-600 text-emerald-300'
                      }`}
                    >
                      {localConfig.insecure_dashboard ? (isAr ? 'مؤقت محلي (10090)' : 'Local (Port 10090)') : (isAr ? 'آمن (Production Router)' : 'Secure (Router + Auth)')}
                    </button>
                  </div>
                </div>

                {/* Form fields */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'منفذ الويب HTTP' : 'HTTP Web Port'}</label>
                    <input
                      type="number"
                      value={localConfig.http_port}
                      onChange={(e) => setLocalConfig({ ...localConfig, http_port: Number(e.target.value) })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'منفذ لوحة التحكم الخارجي' : 'Dashboard External Port'}</label>
                    <input
                      type="number"
                      value={localConfig.dashboard_external_port}
                      onChange={(e) => setLocalConfig({ ...localConfig, dashboard_external_port: Number(e.target.value) })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">{isAr ? 'صلاحية Docker Socket' : 'Docker Socket Mount'}</label>
                    <div className="flex items-center gap-2 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-emerald-400">
                      <Lock className="w-3.5 h-3.5" />
                      <span>/var/run/docker.sock:ro (Read-Only)</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-700/60">
                  <button
                    onClick={() => onUpdateConfig(localConfig)}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-semibold transition-colors"
                  >
                    {isAr ? 'حفظ التعديلات' : 'Save Parameters'}
                  </button>

                  <button
                    disabled={isOperationRunning}
                    onClick={() => onDeployTraefik(localConfig)}
                    className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-mono font-bold shadow-md shadow-cyan-950/40 transition-all flex items-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{isAr ? 'تطبيق ونشر Traefik v3.7' : 'Deploy & Apply to /opt/traefik'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: BACKUPS & SNAPSHOTS */}
          {activeTab === 'backups' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    {isAr ? 'النسخ الاحتياطي والاستعادة لإعدادات Traefik' : 'Traefik Configurations & ACME Snapshots'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {isAr ? 'أرشفة ملفات /opt/traefik والشهادات والمفاتيح مع بصمة SHA256 وأذونات 0600' : 'Secured archives in /opt/traefik/backups with strict 0600 permissions'}
                  </p>
                </div>

                <button
                  onClick={onCreateSnapshot}
                  disabled={isOperationRunning}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-mono flex items-center gap-1.5 shadow-md shadow-emerald-950/40 transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>{isAr ? 'إنشاء نسخة احتياطية فورية' : 'Create Traefik Snapshot'}</span>
                </button>
              </div>

              {/* Snapshots Table */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-800/70 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="py-3 px-4">{isAr ? 'اسم الأرشيف' : 'Archive Name'}</th>
                      <th className="py-3 px-4">{isAr ? 'تاريخ الإنشاء' : 'Timestamp'}</th>
                      <th className="py-3 px-4">{isAr ? 'الحجم' : 'Size'}</th>
                      <th className="py-3 px-4">{isAr ? 'بصمة التشفير SHA256' : 'SHA256 Checksum'}</th>
                      <th className="py-3 px-4 text-right">{isAr ? 'إجراء' : 'Action'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/60 text-slate-300">
                    {snapshots.map((snap) => (
                      <tr key={snap.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-4 font-bold text-cyan-300">{snap.filename}</td>
                        <td className="py-3 px-4 text-slate-400">{snap.timestamp}</td>
                        <td className="py-3 px-4 text-slate-300 tabular-nums">{(snap.size_bytes / 1024).toFixed(1)} KB</td>
                        <td className="py-3 px-4 text-slate-400 text-[10px]">{snap.sha256.substring(0, 20)}...</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setSelectedSnapshotId(snap.id)}
                            className="text-[11px] px-2.5 py-1 rounded bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-800 transition-colors"
                          >
                            {isAr ? 'استعادة' : 'Restore'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Safe Restore Modal / Confirmation Prompt */}
              {selectedSnapshotId && (
                <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800 space-y-3">
                  <div className="flex items-center gap-2 text-rose-400 font-bold text-xs">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{isAr ? 'تأكيد استعادة إعدادات Traefik' : 'Confirm Traefik Snapshot Restoration'}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {isAr
                      ? 'سيتم استبدال ملفات docker-compose.yml و acme.json بالنسخة المحددة. سيتم إنشاء نسخة أمان تلقائية (Rollback Guard) قبل الاستعادة.'
                      : 'Existing Traefik compose and certificate files will be restored. An automated safety rollback snapshot will be created.'}
                  </p>
                  <div className="flex items-center gap-3 pt-1">
                    <button
                      onClick={() => {
                        onRestoreSnapshot(selectedSnapshotId);
                        setSelectedSnapshotId(null);
                      }}
                      className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs font-mono"
                    >
                      {isAr ? 'تأكيد الاستعادة الآن' : 'Execute Safe Restore'}
                    </button>
                    <button
                      onClick={() => setSelectedSnapshotId(null)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono"
                    >
                      {isAr ? 'إلغاء' : 'Cancel'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: CONTROL & LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-6">
              {/* Lifecycle Buttons */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-200">{isAr ? 'التحكم بدورة حياة الحاوية' : 'Traefik Container Lifecycle'}</h4>
                  <p className="text-[11px] text-slate-400">{isAr ? 'تشغيل أو إيقاف أو إعادة تشغيل بدون المساس بالحاويات الأخرى' : 'Targeted lifecycle without affecting Odoo or Postgres instances'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={onStartContainer}
                    disabled={isOperationRunning}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-mono flex items-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{isAr ? 'تشغيل' : 'Start'}</span>
                  </button>
                  <button
                    onClick={onRestartContainer}
                    disabled={isOperationRunning}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs font-mono flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{isAr ? 'إعادة تشغيل' : 'Restart'}</span>
                  </button>
                  <button
                    onClick={onStopContainer}
                    disabled={isOperationRunning}
                    className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs font-mono flex items-center gap-1.5"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>{isAr ? 'إيقاف آمن' : 'Stop'}</span>
                  </button>
                </div>
              </div>

              {/* Live Log Container */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-mono">docker logs --tail 30 traefik</span>
                  <span className="text-[11px] font-mono text-cyan-400">{isAr ? 'محدث حي' : 'Live stream'}</span>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 space-y-1 max-h-80 overflow-y-auto">
                  <div className="text-cyan-400"># Traefik v3.7 Ingress Controller Output:</div>
                  <div>time="2026-11-01T10:28:12Z" level=info msg="Configuration loaded from flags."</div>
                  <div>time="2026-11-01T10:28:12Z" level=info msg="Traefik version 3.7.0 built on 2026-02-14"</div>
                  <div>time="2026-11-01T10:28:12Z" level=info msg="Starting provider *docker.Provider"</div>
                  <div>time="2026-11-01T10:28:13Z" level=info msg="Starting server on :80" entryPointName=web</div>
                  <div>time="2026-11-01T10:28:13Z" level=info msg="Starting server on :8080" entryPointName=traefik</div>
                  <div className="text-emerald-400">time="2026-11-01T10:28:14Z" level=info msg="Router odoo17@docker registered with rule Host(`odoo17.devops-odoo.internal`)"</div>
                  <div className="text-emerald-400">time="2026-11-01T10:28:14Z" level=info msg="Router odoo19@docker registered with rule Host(`odoo19.devops-odoo.internal`)"</div>
                  <div className="text-emerald-400">time="2026-11-01T10:28:15Z" level=info msg="Router jenkins@docker registered on internal port 8081"</div>
                  <div className="text-cyan-400">time="2026-11-01T10:28:15Z" level=info msg="Server has started listening on all configured entrypoints."</div>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400 shrink-0">
          <div className="font-mono flex items-center gap-2">
            <span>Container: <strong className="text-slate-200">traefik</strong></span>
            <span>•</span>
            <span>Network: <strong className="text-cyan-400">proxy</strong></span>
            <span>•</span>
            <span>Dashboard: <strong className="text-cyan-400">http://localhost:10090/dashboard/</strong></span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium transition-colors"
          >
            {isAr ? 'إغلاق النافذة' : 'Close Module'}
          </button>
        </div>

      </div>
    </div>
  );
};
