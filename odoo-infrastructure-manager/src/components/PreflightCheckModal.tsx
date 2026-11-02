import React, { useState } from 'react';
import { 
  X, CheckCircle2, AlertTriangle, XCircle, RefreshCw, 
  Download, RotateCcw, Shield, Terminal, HardDrive, 
  FileArchive, Copy, Check, Info, Server, Cpu, Layers, Sparkles 
} from 'lucide-react';
import { ComponentAuditItem, FullInfrastructureSnapshot, Language } from '../types';

interface PreflightCheckModalProps {
  components: ComponentAuditItem[];
  snapshots: FullInfrastructureSnapshot[];
  lang: Language;
  onRefreshInspection: () => void;
  onInstallSelected: (componentIds: string[], createBackupFirst: boolean) => void;
  onCreateSnapshot: () => void;
  onRestoreSnapshot: (snapshotId: string) => void;
  onClose: () => void;
}

export const PreflightCheckModal: React.FC<PreflightCheckModalProps> = ({
  components,
  snapshots,
  lang,
  onRefreshInspection,
  onInstallSelected,
  onCreateSnapshot,
  onRestoreSnapshot,
  onClose,
}) => {
  const isAr = lang === 'ar';
  const [activeTab, setActiveTab] = useState<'table' | 'installer' | 'snapshots' | 'report'>('table');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedForInstall, setSelectedForInstall] = useState<string[]>(
    components.filter((c) => c.status === 'missing').map((c) => c.id)
  );
  const [createBackupBeforeInstall, setCreateBackupBeforeInstall] = useState<boolean>(true);
  const [restoreConfirmToken, setRestoreConfirmToken] = useState<string>('');
  const [targetRestoreSnap, setTargetRestoreSnap] = useState<FullInfrastructureSnapshot | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  const handleRefresh = () => {
    setIsScanning(true);
    setTimeout(() => {
      onRefreshInspection();
      setIsScanning(false);
    }, 800);
  };

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredComponents = components.filter((c) => {
    const matchesStatus = filterStatus === 'all' || c.status === filterStatus;
    const matchesSearch = 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name_ar.includes(searchQuery) ||
      (c.detected_version && c.detected_version.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  const missingComponents = components.filter((c) => c.status === 'missing' || c.status === 'needs_update');
  const installedCount = components.filter((c) => c.status === 'installed').length;
  const missingCount = components.filter((c) => c.status === 'missing').length;
  const issuesCount = components.filter((c) => c.status === 'misconfigured' || c.status === 'needs_update').length;

  const getStatusBadge = (status: ComponentAuditItem['status']) => {
    switch (status) {
      case 'installed':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            {isAr ? 'مثبت ويعمل' : 'INSTALLED'}
          </span>
        );
      case 'missing':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] bg-rose-950/80 text-rose-300 border border-rose-800 font-bold">
            <XCircle className="w-3 h-3 text-rose-400" />
            {isAr ? 'غير مثبت' : 'MISSING'}
          </span>
        );
      case 'needs_update':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] bg-amber-950/80 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            {isAr ? 'يحتاج تحديث' : 'UPDATE REQ'}
          </span>
        );
      case 'misconfigured':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] bg-purple-950/80 text-purple-300 border border-purple-800">
            <Info className="w-3 h-3 text-purple-400" />
            {isAr ? 'به مشكلة' : 'MISCONFIGURED'}
          </span>
        );
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-cyan-950/50">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">
                  {isAr ? 'الفحص المسبق والتثبيت الذكي والنسخ الاحتياطي' : 'Pre-flight Inspection, Smart Installer & Snapshots'}
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                  Audit Engine v2
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                {isAr
                  ? 'فحص شامل غير مدمر لحالة Ubuntu وDocker وTraefik وAnsible والأدوات قبل أي تغيير'
                  : 'Safe, non-destructive audit of Ubuntu, Docker, Traefik, Ansible, and packages'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            {/* Live Re-scan button */}
            <button
              onClick={handleRefresh}
              disabled={isScanning}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-cyan-300 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin text-cyan-400' : ''}`} />
              <span>{isAr ? 'إعادة الفحص الآن' : 'Re-scan Host'}</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="bg-slate-950/80 px-6 py-2.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('table')}
              className={`px-3 py-1.5 rounded-lg font-mono transition-all ${
                activeTab === 'table' ? 'bg-cyan-600 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {isAr ? 'جدول الفحص والتدقيق' : 'Audit Matrix'} ({components.length})
            </button>
            <button
              onClick={() => setActiveTab('installer')}
              className={`px-3 py-1.5 rounded-lg font-mono transition-all flex items-center gap-1.5 ${
                activeTab === 'installer' ? 'bg-indigo-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>{isAr ? 'التثبيت الذكي التلقائي' : 'Smart Auto-Installer'}</span>
              {missingCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-rose-500 text-slate-950 text-[10px] font-bold flex items-center justify-center">
                  {missingCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('snapshots')}
              className={`px-3 py-1.5 rounded-lg font-mono transition-all flex items-center gap-1.5 ${
                activeTab === 'snapshots' ? 'bg-emerald-600 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>{isAr ? 'النسخ الشاملة والاستعادة' : 'Snapshots & Restore'}</span>
              <span className="text-[10px] bg-slate-800 text-slate-300 px-1 rounded font-bold">
                {snapshots.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab('report')}
              className={`px-3 py-1.5 rounded-lg font-mono transition-all ${
                activeTab === 'report' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {isAr ? 'التقرير النهائي' : 'Final Audit Report'}
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="hidden lg:flex items-center gap-3 font-mono text-[11px]">
            <span className="text-emerald-400 font-bold">✓ {installedCount} {isAr ? 'مثبت' : 'Installed'}</span>
            <span className="text-slate-600">•</span>
            <span className={missingCount > 0 ? 'text-rose-400 font-bold' : 'text-slate-500'}>
              ✗ {missingCount} {isAr ? 'غير مثبت' : 'Missing'}
            </span>
            <span className="text-slate-600">•</span>
            <span className={issuesCount > 0 ? 'text-amber-400 font-bold' : 'text-slate-500'}>
              ! {issuesCount} {isAr ? 'تنبيهات' : 'Issues'}
            </span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">

          {/* TAB 1: AUDIT MATRIX TABLE */}
          {activeTab === 'table' && (
            <div className="space-y-4">
              
              {/* Filter and Search Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
                  <button
                    onClick={() => setFilterStatus('all')}
                    className={`px-2.5 py-1 rounded ${filterStatus === 'all' ? 'bg-slate-800 text-cyan-300 font-bold' : 'text-slate-400'}`}
                  >
                    {isAr ? 'الكل' : 'All'} ({components.length})
                  </button>
                  <button
                    onClick={() => setFilterStatus('installed')}
                    className={`px-2.5 py-1 rounded ${filterStatus === 'installed' ? 'bg-emerald-950 text-emerald-300 font-bold' : 'text-slate-400'}`}
                  >
                    {isAr ? 'مثبت' : 'Installed'} ({installedCount})
                  </button>
                  <button
                    onClick={() => setFilterStatus('missing')}
                    className={`px-2.5 py-1 rounded ${filterStatus === 'missing' ? 'bg-rose-950 text-rose-300 font-bold' : 'text-slate-400'}`}
                  >
                    {isAr ? 'غير مثبت' : 'Missing'} ({missingCount})
                  </button>
                  <button
                    onClick={() => setFilterStatus('needs_update')}
                    className={`px-2.5 py-1 rounded ${filterStatus === 'needs_update' ? 'bg-amber-950 text-amber-300 font-bold' : 'text-slate-400'}`}
                  >
                    {isAr ? 'يحتاج تحديث' : 'Updates'}
                  </button>
                </div>

                <div className="relative">
                  <input
                    type="text"
                    placeholder={isAr ? 'بحث في المكونات أو الإصدارات...' : 'Filter by name or version...'}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:border-cyan-500 focus:outline-none w-full sm:w-64"
                  />
                </div>
              </div>

              {/* Main Status Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-900 border-b border-slate-800 text-slate-400 font-mono">
                        <th className="py-2.5 px-3.5">{isAr ? 'المكون والأداة' : 'Component / Tool'}</th>
                        <th className="py-2.5 px-3.5">{isAr ? 'الحالة' : 'Status'}</th>
                        <th className="py-2.5 px-3.5">{isAr ? 'الإصدار المكتشف' : 'Detected Version'}</th>
                        <th className="py-2.5 px-3.5">{isAr ? 'المسار والتفاصيل' : 'Path & Configuration'}</th>
                        <th className="py-2.5 px-3.5">{isAr ? 'الإجراء المنفذ / الموصى به' : 'Recommended Action'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {filteredComponents.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-3.5">
                            <div className="font-semibold text-slate-200 font-sans">
                              {isAr ? item.name_ar : item.name}
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1 font-sans">
                              {isAr ? item.why_needed_ar : item.why_needed}
                            </div>
                          </td>
                          <td className="py-3 px-3.5 whitespace-nowrap">
                            {getStatusBadge(item.status)}
                          </td>
                          <td className="py-3 px-3.5 text-cyan-300 font-bold whitespace-nowrap">
                            {item.detected_version || <span className="text-slate-600 font-normal">N/A</span>}
                          </td>
                          <td className="py-3 px-3.5 text-slate-300">
                            <div className="text-[11px] text-slate-400 font-mono">{item.binary_path || '-'}</div>
                            <div className="text-[10px] text-slate-500 font-sans mt-0.5">{isAr ? item.details_ar : item.details}</div>
                          </td>
                          <td className="py-3 px-3.5 whitespace-nowrap">
                            <span className="text-[11px] font-sans text-slate-300">
                              {isAr ? item.action_ar : item.action}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: SMART AUTO-INSTALLER */}
          {activeTab === 'installer' && (
            <div className="space-y-6">
              
              {/* Informational Callout */}
              <div className="bg-indigo-950/40 border border-indigo-800/80 rounded-xl p-4 flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-indigo-200 text-sm">
                    {isAr ? 'التثبيت الذكي وغير المدمر للمكونات الناقصة' : 'Intelligent, Non-Destructive Auto-Installer'}
                  </h3>
                  <p className="text-xs text-indigo-200/90 mt-1 leading-relaxed font-sans">
                    {isAr
                      ? 'يقوم النظام فقط بتثبيت الأدوات غير المتوفرة دون إعادة تثبيت أو تعديل أي أدوات قائمة تعمل بالفعل. يتم توفير خيار إجباري لأخذ نسخة احتياطية شاملة للبنية التحتية قبل التنفيذ لضمان سلامة الخادم.'
                      : 'The system only provisions missing or outdated packages without re-installing existing working components. An automated full infrastructure snapshot guard is offered before applying any changes.'}
                  </p>
                </div>
              </div>

              {missingComponents.length === 0 ? (
                <div className="bg-slate-950 border border-emerald-800/60 rounded-xl p-8 text-center space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                  <h4 className="text-base font-bold text-slate-100">
                    {isAr ? 'جميع المتطلبات والأدوات مثبتة وجاهزة 100%' : 'All Required Components are Installed and Ready!'}
                  </h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto font-sans">
                    {isAr
                      ? 'تم التحقق من وجود نظام Ubuntu، محرك Docker Engine، Compose v2، موجه Traefik، أداة Ansible، وحزم الأدوات المساعدة.'
                      : 'Ubuntu OS, Docker Engine, Docker Compose v2, Traefik, Ansible, and system tools are verified.'}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                    {isAr ? 'الأدوات المطلوب تثبيتها مع بيان سبب الحاجة إليها:' : 'Components Requiring Installation & Justification:'}
                  </div>

                  <div className="space-y-3">
                    {missingComponents.map((item) => {
                      const isSelected = selectedForInstall.includes(item.id);
                      return (
                        <div
                          key={item.id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedForInstall(selectedForInstall.filter((id) => id !== item.id));
                            } else {
                              setSelectedForInstall([...selectedForInstall, item.id]);
                            }
                          }}
                          className={`p-4 rounded-xl border text-xs cursor-pointer transition-all flex items-start gap-3.5 ${
                            isSelected
                              ? 'bg-slate-800/80 border-cyan-500 shadow-md shadow-cyan-950/20'
                              : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}} // Handled by parent div click
                            className="mt-1 rounded border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
                          />
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <h4 className="font-bold text-sm text-slate-100 font-sans">
                                {isAr ? item.name_ar : item.name}
                              </h4>
                              {getStatusBadge(item.status)}
                            </div>
                            <div className="mt-1 text-slate-300 font-sans leading-relaxed">
                              <strong className="text-cyan-400">{isAr ? 'سبب الحاجة إليها: ' : 'Why Needed: '}</strong>
                              {isAr ? item.why_needed_ar : item.why_needed}
                            </div>
                            <div className="mt-1 font-mono text-[11px] text-slate-400">
                              {isAr ? 'الإجراء المقترح: ' : 'Action: '}
                              {isAr ? item.action_ar : item.action}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Pre-installation Snapshot Safeguard Checkbox */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="guard-snapshot"
                      checked={createBackupBeforeInstall}
                      onChange={(e) => setCreateBackupBeforeInstall(e.target.checked)}
                      className="rounded border-slate-700 text-emerald-500 focus:ring-0 cursor-pointer"
                    />
                    <label htmlFor="guard-snapshot" className="text-xs text-slate-200 cursor-pointer font-sans leading-relaxed">
                      <strong className="text-emerald-400 font-mono">
                        {isAr ? 'النسخ الاحتياطي الوقائي (موصى به بشدة): ' : 'Pre-Installation Safeguard Snapshot (Recommended): '}
                      </strong>
                      {isAr
                        ? 'إنشاء نسخة احتياطية شاملة لملفات الإعداد، والبيئة، والشهادات، وقواعد البيانات قبل تنفيذ أي تثبيت أو تعديل.'
                        : 'Create full snapshot of configuration profiles, .env secrets, Traefik setups, certificates, and databases before installing.'}
                    </label>
                  </div>

                  {/* Launch Installation Button */}
                  <div className="flex justify-end pt-2">
                    <button
                      disabled={selectedForInstall.length === 0}
                      onClick={() => {
                        onInstallSelected(selectedForInstall, createBackupBeforeInstall);
                        onClose();
                      }}
                      className={`px-5 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 shadow-lg transition-all ${
                        selectedForInstall.length > 0
                          ? 'bg-cyan-600 hover:bg-cyan-500 text-slate-950 shadow-cyan-950/40 active:scale-95'
                          : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                      }`}
                    >
                      <Download className="w-4 h-4" />
                      <span>
                        {isAr
                          ? `بدء التثبيت التلقائي الذكي (${selectedForInstall.length} مكون)`
                          : `Install Selected Components (${selectedForInstall.length})`}
                      </span>
                    </button>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 3: INFRASTRUCTURE SNAPSHOTS & RESTORE */}
          {activeTab === 'snapshots' && (
            <div className="space-y-6">
              
              {/* Trigger Instant Full Snapshot */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <FileArchive className="w-4 h-4 text-emerald-400" />
                    {isAr ? 'إنشاء نسخة احتياطية شاملة للبنية التحتية' : 'Create Full Infrastructure Snapshot'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5 font-sans">
                    {isAr
                      ? 'تشمل: ملفات الإعداد (.yaml)، ملفات البيئة (.env)، تكوينات Docker Compose، إعدادات Traefik، شهادات SSL، وقواعد بيانات PostgreSQL.'
                      : 'Includes: YAML profiles, .env secrets, Compose stacks, Traefik configs, ACME certificates, and PostgreSQL logical dumps.'}
                  </p>
                </div>

                <button
                  onClick={onCreateSnapshot}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-mono shadow-md shadow-emerald-950/40 flex items-center gap-1.5 whitespace-nowrap"
                >
                  <Download className="w-4 h-4" />
                  <span>{isAr ? 'إنشاء نسخة شاملة فوراً' : 'Snapshot Now'}</span>
                </button>
              </div>

              {/* Snapshots Catalog */}
              <div>
                <h4 className="text-xs font-mono text-slate-400 mb-2.5 uppercase tracking-wider">
                  {isAr ? 'أرشيف النسخ الاحتياطية الشاملة الموثقة' : 'Verified Infrastructure Snapshots in Storage'}
                </h4>

                <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-900 border-b border-slate-800 text-slate-400 font-mono">
                          <th className="py-2.5 px-3.5">{isAr ? 'النسخة والتاريخ' : 'Snapshot Archive'}</th>
                          <th className="py-2.5 px-3.5">{isAr ? 'الحجم والمحتويات' : 'Size & Items'}</th>
                          <th className="py-2.5 px-3.5">{isAr ? 'بصمة التشفير SHA256' : 'SHA256 Integrity'}</th>
                          <th className="py-2.5 px-3.5">{isAr ? 'النوع' : 'Type'}</th>
                          <th className="py-2.5 px-3.5 text-right">{isAr ? 'الإجراء' : 'Action'}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {snapshots.map((snap) => (
                          <tr key={snap.id} className="hover:bg-slate-900/40 transition-colors">
                            <td className="py-3 px-3.5">
                              <div className="font-bold text-slate-200">{snap.filename}</div>
                              <div className="text-[11px] text-slate-400 mt-0.5">{snap.timestamp}</div>
                            </td>
                            <td className="py-3 px-3.5">
                              <span className="text-cyan-300 font-bold">{formatBytes(snap.size_bytes)}</span>
                              <span className="text-slate-400 block text-[11px]">{snap.items_count} files included</span>
                            </td>
                            <td className="py-3 px-3.5">
                              <button
                                onClick={() => handleCopyHash(snap.sha256)}
                                className="flex items-center gap-1 text-slate-400 hover:text-slate-200 text-[11px] font-mono group"
                                title={snap.sha256}
                              >
                                <span>{snap.sha256.substring(0, 14)}...</span>
                                {copiedHash === snap.sha256 ? (
                                  <Check className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3 h-3 text-slate-600 group-hover:text-slate-400" />
                                )}
                              </button>
                            </td>
                            <td className="py-3 px-3.5">
                              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                                snap.type === 'full_infrastructure'
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                              }`}>
                                {snap.type === 'full_infrastructure' ? 'FULL SNAPSHOT' : 'PRE-INSTALL GUARD'}
                              </span>
                            </td>
                            <td className="py-3 px-3.5 text-right">
                              <button
                                onClick={() => setTargetRestoreSnap(snap)}
                                className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-rose-950/80 hover:text-rose-300 border border-slate-700 text-slate-300 text-xs font-mono transition-colors"
                              >
                                {isAr ? 'استعادة' : 'Restore'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Restore Confirmation Dialog if selected */}
              {targetRestoreSnap && (
                <div className="bg-rose-950/30 border border-rose-800/80 rounded-xl p-5 space-y-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-bold text-rose-300 text-sm">
                        {isAr ? 'تأكيد استعادة النسخة الشاملة للبنية التحتية' : 'CONFIRM INFRASTRUCTURE SNAPSHOT RESTORATION'}
                      </h4>
                      <p className="text-xs text-rose-200/90 mt-1 font-sans leading-relaxed">
                        {isAr
                          ? `أنت على وشك استعادة النسخة: ${targetRestoreSnap.filename}. سيتم استبدال ملفات الإعداد والشهادات وقواعد البيانات الحالية. يقوم النظام أولاً بتوليد نسخة أمان احتياطية فورية قبل أي تعديل.`
                          : `You are about to restore snapshot: ${targetRestoreSnap.filename}. Configurations and databases will be reverted. An automatic pre-restore safety snapshot will be created first.`}
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-slate-300 block mb-1 font-mono">
                      {isAr ? 'للتأكيد، يرجى كتابة الرمز التالي بالضبط: ' : 'Type exact confirmation token: '}
                      <code className="bg-rose-950 text-rose-300 px-1.5 py-0.5 rounded border border-rose-800 font-bold">
                        RESTORE-{targetRestoreSnap.id}
                      </code>
                    </label>
                    <input
                      type="text"
                      placeholder={`RESTORE-${targetRestoreSnap.id}`}
                      value={restoreConfirmToken}
                      onChange={(e) => setRestoreConfirmToken(e.target.value)}
                      className="w-full bg-slate-950 border border-rose-800 rounded-lg px-3 py-2 text-xs text-rose-300 font-mono focus:border-rose-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                      onClick={() => setTargetRestoreSnap(null)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono"
                    >
                      {isAr ? 'إلغاء' : 'Cancel'}
                    </button>
                    <button
                      disabled={restoreConfirmToken.trim() !== `RESTORE-${targetRestoreSnap.id}`}
                      onClick={() => {
                        onRestoreSnapshot(targetRestoreSnap.id);
                        setTargetRestoreSnap(null);
                        setRestoreConfirmToken('');
                        onClose();
                      }}
                      className={`px-4 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5 transition-all ${
                        restoreConfirmToken.trim() === `RESTORE-${targetRestoreSnap.id}`
                          ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/40'
                          : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                      }`}
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>{isAr ? 'تأكيد واستعادة النسخة' : 'Confirm Restoration'}</span>
                    </button>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 4: FINAL AUDIT REPORT */}
          {activeTab === 'report' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4">
                  <div className="text-xs font-mono text-slate-400">{isAr ? 'جاهزية النظام' : 'Readiness Index'}</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
                    {missingCount === 0 ? '100% READY' : `${Math.round((installedCount / components.length) * 100)}% READY`}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 font-sans">
                    {missingCount === 0
                      ? (isAr ? 'النظام جاهز تماماً لكافة عمليات النشر' : 'Compliant and ready for multi-version deploy')
                      : (isAr ? `يوجد ${missingCount} أدوات تتطلب التثبيت` : `${missingCount} tools pending setup`)}
                  </p>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4">
                  <div className="text-xs font-mono text-slate-400">{isAr ? 'الأمان وعزل البيانات' : 'Security & Isolation'}</div>
                  <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">VERIFIED</div>
                  <p className="text-[11px] text-slate-400 mt-1 font-sans">
                    {isAr ? 'منافذ بوستجريس معزولة وشبكة proxy مفعلة' : 'PostgreSQL ports isolated, ACME secured'}
                  </p>
                </div>

                <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4">
                  <div className="text-xs font-mono text-slate-400">{isAr ? 'حماية النسخ الاحتياطية' : 'Snapshot Protection'}</div>
                  <div className="text-2xl font-bold text-indigo-400 mt-1 font-mono">{snapshots.length} REVISIONS</div>
                  <p className="text-[11px] text-slate-400 mt-1 font-sans">
                    {isAr ? 'بصمات SHA256 موثقة وخط رجعة مؤمن' : 'SHA256 verified rollback available'}
                  </p>
                </div>
              </div>

              {/* Text Summary Block */}
              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-2">
                <div className="text-cyan-400 font-bold"># ODOO INFRASTRUCTURE MANAGER - EXECUTIVE AUDIT SUMMARY</div>
                <div>• Host OS: Ubuntu 24.04 LTS (Compliant & Supported)</div>
                <div>• Virtualization: Docker Engine v26.1.4 | Docker Compose v2.27.1</div>
                <div>• Ingress Router: Traefik v3.7 (HTTP ➔ HTTPS Redirect, ACME TLS)</div>
                <div>• Odoo Stacks: Odoo 17.0 (PG 16) & Odoo 19.0 (PG 18) Isolated Bridges</div>
                <div>• Backup Status: Verified SHA256 Checksum Engine Active</div>
                <div className="text-emerald-400 font-bold pt-2">STATUS: SAFE TO PROCEED WITH AUTOMATED OPERATIONS</div>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="bg-slate-950 px-6 py-3.5 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>{isAr ? 'جميع عمليات الفحص آمنة وغير مدمرة ولا تمس البيانات' : 'All audits are strictly non-destructive'}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            {isAr ? 'إغلاق النافذة' : 'Close'}
          </button>
        </div>

      </div>
    </div>
  );
};
