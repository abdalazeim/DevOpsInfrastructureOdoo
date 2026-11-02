import React from 'react';
import { Shield, Server, Database, Globe, Lock, ArrowDown, Activity, HardDrive, Cpu } from 'lucide-react';
import { InfrastructureProfile, ContainerRuntimeHealth, Language } from '../types';

interface TopologyViewProps {
  profile: InfrastructureProfile;
  containers: ContainerRuntimeHealth[];
  lang: Language;
  onSelectService: (serviceName: string) => void;
}

export const TopologyView: React.FC<TopologyViewProps> = ({
  profile,
  containers,
  lang,
  onSelectService,
}) => {
  const isAr = lang === 'ar';

  const getContainer = (name: string) => containers.find((c) => c.name === name);

  const traefik = getContainer('traefik');
  const odoo17 = getContainer('odoo17');
  const pg16 = getContainer('odoo17-db');
  const odoo19 = getContainer('odoo19');
  const pg18 = getContainer('odoo19-db');

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl relative overflow-hidden">
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:16px_16px] opacity-20 pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6 border-b border-slate-800/80 pb-4 relative z-10">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            {isAr ? 'البنية الهيكلية لشبكة الحاويات والتوجيه' : 'Multi-Version Infrastructure Topology'}
          </h2>
          <p className="text-xs text-slate-400">
            {isAr
              ? 'مخطط تدفق الاتصالات، عزل الشبكات، وحماية قواعد بيانات PostgreSQL'
              : 'Container network topology, reverse proxy routing, and isolated database networks'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
            <Lock className="w-3 h-3 text-emerald-400" />
            Let's Encrypt TLS: {profile.traefik.enabled ? 'ACME Active' : 'Disabled'}
          </span>
          <span className="px-2.5 py-1 rounded bg-cyan-950/60 border border-cyan-800 text-cyan-300">
            Net: {profile.network.proxy_network_name} ({profile.network.proxy_subnet})
          </span>
        </div>
      </div>

      {/* Main Diagram Area */}
      <div className="flex flex-col items-center gap-4 relative z-10">

        {/* 1. Public Ingress & Traefik v3.7 */}
        <div className="w-full max-w-2xl bg-gradient-to-b from-slate-800/90 to-slate-900 border border-cyan-500/30 rounded-xl p-3.5 shadow-lg shadow-cyan-950/30">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-slate-100">Traefik v3.7 Reverse Proxy</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                    {traefik?.healthcheck || 'healthy'}
                  </span>
                </div>
                <div className="text-xs font-mono text-cyan-300 mt-0.5 flex flex-wrap gap-2">
                  <span>Port 80 (HTTP ➔ 301)</span>
                  <span>•</span>
                  <span>Port 10090 (Dashboard)</span>
                  <span>•</span>
                  <span>Port 443 (HTTPS)</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center">
              <span className="text-[11px] font-mono bg-slate-800 px-2 py-0.5 rounded text-cyan-300 border border-slate-700">
                :10090/dashboard/
              </span>
              <button
                onClick={() => onSelectService('traefik')}
                className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline px-2 py-1 font-mono"
              >
                {isAr ? 'السجلات' : 'Logs'}
              </button>
            </div>
          </div>
        </div>

        {/* Connecting Arrow to Shared Proxy Network */}
        <div className="flex items-center gap-2 text-slate-500 text-xs font-mono">
          <ArrowDown className="w-4 h-4 text-cyan-400 animate-bounce" />
          <span>Docker Bridge: <code className="text-cyan-300 font-bold">{profile.network.proxy_network_name}</code> (Shared Proxy Layer)</span>
          <ArrowDown className="w-4 h-4 text-cyan-400 animate-bounce" />
        </div>

        {/* 2. Dual Stacks: Odoo 17 (Left) & Odoo 19 (Right) */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* STACK ODOO 17 */}
          <div className="bg-slate-800/40 border border-indigo-500/30 rounded-xl p-4 flex flex-col gap-3 relative">
            <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse" />
                <h3 className="font-bold text-sm text-indigo-300">Odoo 17 Production Stack</h3>
              </div>
              <span className="text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded">
                v17.0
              </span>
            </div>

            {/* Odoo 17 Web Container */}
            <div
              onClick={() => onSelectService('odoo17')}
              className="bg-slate-900/80 border border-slate-700 rounded-lg p-3 hover:border-indigo-400 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Globe className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">odoo17 (Web Application)</div>
                    <div className="text-[11px] font-mono text-slate-400">{profile.odoo17.domain}</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono text-emerald-400 block">HTTP 8069 / WS 8072</span>
                  <span className="text-[10px] text-slate-400 font-mono">Workers: {profile.odoo17.workers}</span>
                </div>
              </div>
            </div>

            {/* Internal Isolated Network Bridge */}
            <div className="flex items-center justify-center gap-1.5 py-0.5 text-[11px] font-mono text-slate-500">
              <Lock className="w-3 h-3 text-amber-400" />
              <span>Isolated Network: <code className="text-amber-300">odoo17_internal</code></span>
            </div>

            {/* PostgreSQL 16 DB Container */}
            <div
              onClick={() => onSelectService('odoo17-db')}
              className="bg-slate-900/80 border border-slate-700 rounded-lg p-3 hover:border-emerald-400 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">odoo17-db (PostgreSQL 16)</div>
                    <div className="text-[11px] font-mono text-slate-400">{profile.odoo17.database.name} ({profile.odoo17.database.engine})</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    Port 5432 (Internal)
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">No Public Port</span>
                </div>
              </div>
            </div>

            {/* Volumes badge */}
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-900/40 p-2 rounded border border-slate-800">
              <span className="flex items-center gap-1">
                <HardDrive className="w-3 h-3 text-slate-400" />
                Volumes:
              </span>
              <span className="text-slate-300">odoo17_data • odoo17_db_data</span>
            </div>
          </div>

          {/* STACK ODOO 19 */}
          <div className="bg-slate-800/40 border border-purple-500/30 rounded-xl p-4 flex flex-col gap-3 relative">
            <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
                <h3 className="font-bold text-sm text-purple-300">Odoo 19 Next-Gen Stack</h3>
              </div>
              <span className="text-[10px] font-mono bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded">
                v19.0
              </span>
            </div>

            {/* Odoo 19 Web Container */}
            <div
              onClick={() => onSelectService('odoo19')}
              className="bg-slate-900/80 border border-slate-700 rounded-lg p-3 hover:border-purple-400 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Globe className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">odoo19 (Web Application)</div>
                    <div className="text-[11px] font-mono text-slate-400">{profile.odoo19.domain}</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono text-purple-400 block">HTTP 10019 / 8069 / WS 8072</span>
                  <span className="text-[10px] text-slate-400 font-mono">Workers: {profile.odoo19.workers}</span>
                </div>
              </div>
            </div>

            {/* Internal Isolated Network Bridge */}
            <div className="flex items-center justify-center gap-1.5 py-0.5 text-[11px] font-mono text-slate-500">
              <Lock className="w-3 h-3 text-amber-400" />
              <span>Isolated Network: <code className="text-amber-300">odoo19_internal</code></span>
            </div>

            {/* PostgreSQL 18 DB Container */}
            <div
              onClick={() => onSelectService('odoo19-db')}
              className="bg-slate-900/80 border border-slate-700 rounded-lg p-3 hover:border-emerald-400 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">odoo19-db (PostgreSQL 18)</div>
                    <div className="text-[11px] font-mono text-slate-400">{profile.odoo19.database.name} ({profile.odoo19.database.engine})</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    Port 5432 (Internal)
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">No Public Port</span>
                </div>
              </div>
            </div>

            {/* Volumes badge */}
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-900/40 p-2 rounded border border-slate-800">
              <span className="flex items-center gap-1">
                <HardDrive className="w-3 h-3 text-slate-400" />
                Volumes:
              </span>
              <span className="text-slate-300">odoo19_data • odoo19_db_data</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
