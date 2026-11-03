import React from 'react';
import { Server, Shield, Globe, Sliders, FileCode, CheckCircle2, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { InfrastructureProfile, Language } from '../types';

interface HeaderProps {
  currentProfile: InfrastructureProfile;
  profiles: InfrastructureProfile[];
  onSelectProfile: (profile: InfrastructureProfile) => void;
  lang: Language;
  onToggleLang: () => void;
  dryRun: boolean;
  onToggleDryRun: () => void;
  onOpenProfileEditor: () => void;
  onOpenFilesModal: () => void;
  onOpenPreflightModal: () => void;
  onOpenTraefikModal: () => void;
  activeContainersCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  currentProfile,
  profiles,
  onSelectProfile,
  lang,
  onToggleLang,
  dryRun,
  onToggleDryRun,
  onOpenProfileEditor,
  onOpenFilesModal,
  onOpenPreflightModal,
  onOpenTraefikModal,
  activeContainersCount,
}) => {
  const isAr = lang === 'ar';

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-slate-100 sticky top-0 z-40 backdrop-blur-md bg-slate-900/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Logo & Branding */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 p-0.5 shadow-lg shadow-cyan-900/20 flex items-center justify-center">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Server className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-base sm:text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">
                  {isAr ? 'مدير البنية التحتية لأودو' : 'Odoo Infrastructure Manager'}
                </h1>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                  v1.0 (17 / 18 / 19)
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono hidden sm:block">
                Ubuntu {currentProfile.server.hostname} • Traefik v3.7 • Docker Engine
              </p>
            </div>
          </div>

          {/* Controls: Profile Selector, Dry Run, Files, Language */}
          <div className="flex items-center gap-2 sm:gap-3">
            
            {/* Containers Health Badge */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs font-mono">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>{activeContainersCount}/5 {isAr ? 'حاويات نشطة' : 'Containers Healthy'}</span>
            </div>

            {/* Profile Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-lg px-2 py-1 text-xs">
              <Sliders className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={currentProfile.profile_name}
                onChange={(e) => {
                  const target = profiles.find((p) => p.profile_name === e.target.value);
                  if (target) onSelectProfile(target);
                }}
                className="bg-transparent text-slate-200 focus:outline-none cursor-pointer font-mono text-xs pr-2"
              >
                {profiles.map((p) => (
                  <option key={p.profile_name} value={p.profile_name} className="bg-slate-900 text-slate-200">
                    {p.profile_name} ({p.server.hostname})
                  </option>
                ))}
              </select>
            </div>

            {/* Dry-Run Toggle */}
            <button
              onClick={onToggleDryRun}
              title={isAr ? 'تفعيل أو تعطيل وضع المعاينة والمحاكاة' : 'Toggle Dry-Run Simulation Mode'}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border ${
                dryRun
                  ? 'bg-amber-950/80 border-amber-500/80 text-amber-300 shadow-sm shadow-amber-900/30'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className={`w-3.5 h-3.5 ${dryRun ? 'text-amber-400' : 'text-slate-400'}`} />
              <span className="hidden sm:inline">Dry-Run:</span>
              <span className="font-mono">{dryRun ? (isAr ? 'مفعّل' : 'ON') : (isAr ? 'معطّل' : 'OFF')}</span>
            </button>

            {/* Traefik Manager Button */}
            <button
              onClick={onOpenTraefikModal}
              title={isAr ? 'وحدة إدارة Traefik على Docker' : 'Traefik Docker Management Module'}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-700/80 text-cyan-300 font-bold text-xs font-mono shadow-sm transition-all active:scale-95"
            >
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'إدارة Traefik' : 'Traefik'}</span>
            </button>

            {/* Preflight Inspection Button */}
            <button
              onClick={onOpenPreflightModal}
              title={isAr ? 'فحص المتطلبات والتثبيت الذكي والنسخ الشاملة' : 'Pre-flight Inspection & Smart Installer'}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-gradient-to-r from-cyan-600/90 to-indigo-600/90 hover:from-cyan-500 hover:to-indigo-500 text-slate-950 font-bold text-xs font-mono shadow-md shadow-cyan-950/40 transition-all active:scale-95"
            >
              <Shield className="w-3.5 h-3.5 fill-current" />
              <span>{isAr ? 'الفحص المسبق' : 'Pre-flight'}</span>
            </button>

            {/* Config & Files Modals Buttons */}
            <button
              onClick={onOpenProfileEditor}
              title={isAr ? 'تحرير ملف الإعداد والتحقق من صحته' : 'Edit and validate active profile'}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <Sliders className="w-4 h-4" />
            </button>

            <button
              onClick={onOpenFilesModal}
              title={isAr ? 'عرض ملفات Compose و Ansible والسكربتات' : 'Inspect Compose, Ansible, and Bash files'}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <FileCode className="w-4 h-4" />
            </button>

            {/* Language Switcher */}
            <button
              onClick={onToggleLang}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-300 transition-colors"
              title={isAr ? 'التبديل إلى الإنجليزية' : 'Switch to Arabic'}
            >
              <Globe className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'English' : 'العربية'}</span>
            </button>

          </div>
        </div>
      </div>
    </header>
  );
};
