import React, { useState } from 'react';
import { 
  Server, Shield, Globe, Layers, Database, 
  RotateCcw, Activity, Play, AlertTriangle, Cpu, 
  Download, Network, Lock, Sliders, Wrench, FileCode, CheckCircle2
} from 'lucide-react';
import { OperationCategory, Language } from '../types';

interface OperationsMenuProps {
  lang: Language;
  onLaunchOperation: (category: OperationCategory) => void;
  onOpenDatabaseManager: () => void;
  onOpenPreflight: () => void;
  onOpenTraefikManager: () => void;
  onOpenOdooManager: () => void;
  onOpenProfileEditor: () => void;
  isOperationRunning: boolean;
}

export const OperationsMenu: React.FC<OperationsMenuProps> = ({
  lang,
  onLaunchOperation,
  onOpenDatabaseManager,
  onOpenPreflight,
  onOpenTraefikManager,
  onOpenOdooManager,
  onOpenProfileEditor,
  isOperationRunning,
}) => {
  const isAr = lang === 'ar';
  const [selectedGroup, setSelectedGroup] = useState<'all' | 'system' | 'infra' | 'odoo' | 'backup' | 'obs'>('all');

  const operations = [
    {
      num: 1,
      id: 'system_info',
      category: 'system_info' as const,
      group: 'system',
      icon: Cpu,
      name: 'System Information',
      name_ar: 'معلومات النظام والخادم',
      description: 'Audits Ubuntu release, Linux kernel, CPU cores, RAM allocation, and persistent disk usage.',
      description_ar: 'فحص إصدار التوزيعة ورقم النواة وعتاد المعالج والذاكرة ومسارات التخزين.',
      timeEstimate: '~5s',
      risk: 'low',
    },
    {
      num: 2,
      id: 'health',
      category: 'health' as const,
      group: 'system',
      icon: Activity,
      name: 'Infrastructure Health Check',
      name_ar: 'فحص الصحة والتشخيص الشامل',
      description: 'Probes Docker daemon, bridge network IPAM, and container healthchecks across all 5 stacks.',
      description_ar: 'فحص حي لحالة محرك دوكر، شبكة البروكسي، ومؤشرات صحة الحاويات الخمس.',
      timeEstimate: '~10s',
      risk: 'low',
    },
    {
      num: 3,
      id: 'install_components',
      category: 'install_components' as const,
      group: 'system',
      icon: Shield,
      name: 'Install Missing Components',
      name_ar: 'الفحص المسبق والتثبيت الذكي',
      description: 'Non-destructive pre-flight audit with explanations of why each tool is needed and safe snapshot guard.',
      description_ar: 'فحص شامل وتثبيت الحزم المفقودة تلقائياً مع توضيح سبب الحاجة ونسخة أمان.',
      timeEstimate: '~30s',
      risk: 'medium',
      specialAction: 'preflight',
    },
    {
      num: 4,
      id: 'docker_mgmt',
      category: 'docker_mgmt' as const,
      group: 'infra',
      icon: Server,
      name: 'Docker Management',
      name_ar: 'إدارة محرك دوكر والحاويات',
      description: 'Manages daemon engine, inspects cgroup v2, audits container restart counters, and checks storage driver.',
      description_ar: 'التحكم بالمحرك، مراقبة الحاويات، وتأكيد سياسة unless-stopped لإعادة التشغيل.',
      timeEstimate: '~15s',
      risk: 'low',
    },
    {
      num: 5,
      id: 'traefik',
      category: 'traefik' as const,
      group: 'infra',
      icon: Shield,
      name: 'Traefik Management',
      name_ar: 'إدارة موجه ترافيك Traefik v3.7',
      description: 'Dedicated Ubuntu module: ports 80/10090, proxy network, router labels for Odoo & Jenkins, and backups.',
      description_ar: 'وحدة مخصصة: ضبط المنافذ 80 و 10090، شبكة proxy، ملصقات التوجيه والنسخ الاحتياطي.',
      timeEstimate: '~25s',
      risk: 'medium',
      specialAction: 'traefik_modal',
    },
    {
      num: 6,
      id: 'network_mgmt',
      category: 'network_mgmt' as const,
      group: 'infra',
      icon: Network,
      name: 'Docker Network Management',
      name_ar: 'إدارة شبكات دوكر والعزل الأمني',
      description: 'Audits shared proxy bridge (172.28.0.0/16) and guarantees isolated internal networks for databases.',
      description_ar: 'فحص شبكة proxy المشتركة والتأكد من العزل التام لشبكات قواعد البيانات الداخلية.',
      timeEstimate: '~10s',
      risk: 'low',
    },
    {
      num: 7,
      id: 'odoo17',
      category: 'odoo17' as const,
      group: 'odoo',
      icon: Globe,
      name: 'Odoo 17 Management',
      name_ar: 'إدارة ونشر Odoo 17 & PostgreSQL 16',
      description: 'Deploys odoo17 and isolated odoo17-db, checks pg_isready socket, and binds Traefik web & livechat routers.',
      description_ar: 'تشغيل حاويات Odoo 17 وقاعدة PostgreSQL 16 المعزولة، وفحص الجاهزية وربط التوجيه.',
      timeEstimate: '~60s',
      risk: 'medium',
    },
    {
      num: 8,
      id: 'odoo19',
      category: 'odoo19' as const,
      group: 'odoo',
      icon: Globe,
      name: 'Odoo 19 Management',
      name_ar: 'إدارة ونشر Odoo 19 & PostgreSQL 18',
      description: 'Deploys next-gen Odoo 19 with PostgreSQL 18, validates memory ceilings, and binds ingress port 10019/80.',
      description_ar: 'تشغيل بيئة Odoo 19 وقاعدة PostgreSQL 18، التحقق من حدود الذاكرة والتوجيه المشفر.',
      timeEstimate: '~60s',
      risk: 'medium',
    },
    {
      num: 9,
      id: 'postgres_mgmt',
      category: 'postgres_mgmt' as const,
      group: 'odoo',
      icon: Database,
      name: 'PostgreSQL Management',
      name_ar: 'إدارة خوادم قواعد البيانات بوستجريس',
      description: 'Probes PG16 and PG18 sockets via pg_isready and strictly verifies port 5432 is internal only (never public).',
      description_ar: 'فحص جاهزية محركات بوستجريس 16 و 18 والتأكيد الحاسم على عدم كشف المنفذ 5432 خارجياً.',
      timeEstimate: '~15s',
      risk: 'low',
    },
    {
      num: 10,
      id: 'dns_ssl',
      category: 'dns_ssl' as const,
      group: 'backup',
      icon: Lock,
      name: 'DNS & SSL Verification',
      name_ar: 'التحقق من سجلات النطاقات وتشفير SSL',
      description: 'Tests DNS A-records, port 80/443 reachability, and audits acme.json with strict 0600 permissions.',
      description_ar: 'التحقق من توجيه النطاقات، خلو المنافذ 80 و 443، وتأكيد صلاحيات 0600 المشددة للشهادات.',
      timeEstimate: '~15s',
      risk: 'low',
    },
    {
      num: 11,
      id: 'backup',
      category: 'backup' as const,
      group: 'backup',
      icon: Database,
      name: 'Backup Management',
      name_ar: 'إدارة النسخ الاحتياطي لقواعد البيانات',
      description: 'Streams safe pg_dump to gzip, archives filestore, verifies SHA256 checksum, and enforces retention count.',
      description_ar: 'استخراج تفريغ مضغوط للقواعد، أرشفة المرفقات، توليد بصمة SHA256، وتطبيق سياسة الحفظ.',
      timeEstimate: '~20s',
      risk: 'low',
      specialAction: 'database_modal',
    },
    {
      num: 12,
      id: 'restore',
      category: 'restore' as const,
      group: 'backup',
      icon: RotateCcw,
      name: 'Restore Management',
      name_ar: 'استعادة النسخ الاحتياطية الآمنة',
      description: 'Safely restores SQL archives with automatic pre-restore rollback snapshots and typed confirmation tokens.',
      description_ar: 'استعادة موثوقة لأرشيف SQL مع توليد نسخة أمان تلقائية وطلب تأكيد كتابي صريح.',
      timeEstimate: '~40s',
      risk: 'critical',
      specialAction: 'database_modal',
    },
    {
      num: 13,
      id: 'monitoring_logs',
      category: 'monitoring_logs' as const,
      group: 'obs',
      icon: Activity,
      name: 'Monitoring & Logs',
      name_ar: 'مراقبة أداء الخدمات واستعراض السجلات',
      description: 'Inspects live logs across Traefik, Odoo 17, and Odoo 19, and summarizes CPU/memory utilization.',
      description_ar: 'استعراض السجلات الحية لجميع الخدمات وقياس استهلاك المعالج والذاكرة بدقة.',
      timeEstimate: '~10s',
      risk: 'low',
    },
    {
      num: 14,
      id: 'profiles',
      category: 'profiles' as const,
      group: 'obs',
      icon: Sliders,
      name: 'Configuration Profiles',
      name_ar: 'ملفات الإعداد والتكوين (Profiles)',
      description: 'Validates YAML syntax, port overlap boundaries, memory limits, and ensures secrets remain in .env.',
      description_ar: 'تدقيق ملفات YAML، منع تسريب كلمات المرور، والتحقق من عدم تعارض المنافذ.',
      timeEstimate: '~5s',
      risk: 'low',
      specialAction: 'profile_modal',
    },
    {
      num: 15,
      id: 'troubleshooting',
      category: 'troubleshooting' as const,
      group: 'obs',
      icon: Wrench,
      name: 'Troubleshooting & Diagnostics',
      name_ar: 'استكشاف الأعطال والتشخيص التلقائي',
      description: 'Detects ingress port blockers, exited containers, and disk space inode saturation with fix advice.',
      description_ar: 'اكتشاف تعارض المنافذ، الحاويات المتعطلة، ونفاد مساحة القرص مع تقديم حلول مقترحة.',
      timeEstimate: '~15s',
      risk: 'low',
    },
    {
      num: 16,
      id: 'infra_report',
      category: 'infra_report' as const,
      group: 'obs',
      icon: Download,
      name: 'Generate Infrastructure Report',
      name_ar: 'توليد التقرير الشامل للبنية التحتية',
      description: 'Compiles complete environment audit markdown report with timestamps and verification results.',
      description_ar: 'بناء وتوليد وثيقة فحص شاملة بتنسيق Markdown وتوثيق حالة كافة المكونات.',
      timeEstimate: '~10s',
      risk: 'low',
    },
  ];

  const filteredOps = selectedGroup === 'all' 
    ? operations 
    : operations.filter((op) => op.group === selectedGroup);

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'low':
        return <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800">LOW RISK</span>;
      case 'medium':
        return <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-blue-950/80 text-blue-400 border border-blue-800">STANDARD</span>;
      case 'high':
        return <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-amber-950/80 text-amber-400 border border-amber-800">IMPACTFUL</span>;
      case 'critical':
        return (
          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-rose-950/80 text-rose-400 border border-rose-800 font-bold flex items-center gap-1">
            <AlertTriangle className="w-2.5 h-2.5" /> CRITICAL
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl">
      {/* Top Banner with Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>{isAr ? 'قائمة عمليات إدارة البنية التحتية (16 خياراً)' : 'Infrastructure Operations Catalog (16 Enterprise Options)'}</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {isAr 
              ? 'تطابق كامل مع خيارات Terminal Menu لتنفيذ وإدارة الخادم و Traefik و Odoo 17 و 19 والقواعد' 
              : 'Direct counterpart to the terminal interactive menu with automated pipelines and live logs'}
          </p>
        </div>

        {/* Global Action Launchers */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onLaunchOperation('backup')}
            className="text-xs bg-blue-950 hover:bg-blue-900 text-blue-300 border border-blue-700/80 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors shadow-sm"
          >
            <Database className="w-3.5 h-3.5 text-blue-400" />
            <span>{isAr ? 'نسخ احتياطي شامل' : 'Full Backup'}</span>
          </button>

          <button
            onClick={() => onLaunchOperation('restore')}
            className="text-xs bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-700/80 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
            <span>{isAr ? 'استعادة النظام' : 'Restore System'}</span>
          </button>

          <button
            onClick={onOpenTraefikManager}
            className="text-xs bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-700/80 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors shadow-sm"
          >
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>{isAr ? 'وحدة Traefik المخصصة' : 'Traefik Console'}</span>
          </button>

          <button
            onClick={onOpenOdooManager}
            className="text-xs bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-700/80 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors shadow-sm"
          >
            <Globe className="w-3.5 h-3.5 text-indigo-400" />
            <span>{isAr ? 'إدارة Odoo' : 'Odoo Manager'}</span>
          </button>

          <button
            onClick={onOpenPreflight}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-700/80 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors shadow-sm"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>{isAr ? 'الفحص المسبق الذكي' : 'Smart Preflight'}</span>
          </button>

          <button
            onClick={onOpenDatabaseManager}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono transition-colors"
          >
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>{isAr ? 'النسخ والقواعد' : 'Database Backups'}</span>
          </button>

          <button
            disabled={isOperationRunning}
            onClick={() => onLaunchOperation('full_deploy')}
            className="text-xs bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-slate-950 font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-mono shadow-md shadow-cyan-950/40 transition-all active:scale-95 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{isAr ? 'النشر المتكامل الشامل' : 'Full Deployment Pipeline'}</span>
          </button>
        </div>
      </div>

      {/* Segmented Filter Controls */}
      <div className="flex items-center gap-1.5 mb-5 p-1 bg-slate-950/60 rounded-xl border border-slate-800/80 overflow-x-auto text-xs font-mono">
        <button
          onClick={() => setSelectedGroup('all')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'all' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'جميع العمليات (16)' : 'All 16 Operations'}
        </button>
        <button
          onClick={() => setSelectedGroup('system')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'system' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'النظام والخادم (1-3)' : 'System & Setup (1-3)'}
        </button>
        <button
          onClick={() => setSelectedGroup('infra')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'infra' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'دوكر وترافيك (4-6)' : 'Docker & Traefik (4-6)'}
        </button>
        <button
          onClick={() => setSelectedGroup('odoo')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'odoo' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'أودو والقواعد (7-9)' : 'Odoo & Postgres (7-9)'}
        </button>
        <button
          onClick={() => setSelectedGroup('backup')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'backup' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'الأمان والنسخ (10-12)' : 'Security & Backups (10-12)'}
        </button>
        <button
          onClick={() => setSelectedGroup('obs')}
          className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
            selectedGroup === 'obs' ? 'bg-cyan-600 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAr ? 'المراقبة والتقارير (13-16)' : 'Diagnostics & Reports (13-16)'}
        </button>
      </div>

      {/* Operations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {filteredOps.map((op) => {
          const Icon = op.icon;
          return (
            <div
              key={op.id}
              className="bg-slate-800/40 border border-slate-700/80 hover:border-cyan-500/50 rounded-xl p-4 flex flex-col justify-between transition-all hover:shadow-lg hover:shadow-cyan-950/20 group relative overflow-hidden"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-md bg-slate-900 border border-slate-700 text-cyan-400 flex items-center justify-center font-mono font-bold text-xs">
                      {op.num}
                    </span>
                    <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-400 group-hover:bg-cyan-500/10 transition-colors">
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>
                  {getRiskBadge(op.risk)}
                </div>

                <h3 className="text-sm font-bold text-slate-100 group-hover:text-cyan-300 transition-colors">
                  {isAr ? op.name_ar : op.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1.5 leading-relaxed line-clamp-3">
                  {isAr ? op.description_ar : op.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-700/60 flex items-center justify-between">
                <span className="text-[11px] font-mono text-slate-400">{op.timeEstimate}</span>
                
                <div className="flex items-center gap-1.5">
                  {op.id === 'traefik' && (
                    <button
                      onClick={onOpenTraefikManager}
                      className="px-2 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition-colors"
                      title={isAr ? 'فتح نافذة إدارة Traefik المخصصة' : 'Open Traefik Management Console'}
                    >
                      {isAr ? 'تخصيص' : 'Console'}
                    </button>
                  )}

                  <button
                    disabled={isOperationRunning}
                    onClick={() => {
                      if (op.specialAction === 'preflight') {
                        onOpenPreflight();
                      } else if (op.specialAction === 'database_modal') {
                        onOpenDatabaseManager();
                      } else if (op.specialAction === 'profile_modal') {
                        onOpenProfileEditor();
                      } else {
                        onLaunchOperation(op.category);
                      }
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition-all ${
                      isOperationRunning
                        ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                        : 'bg-cyan-600 hover:bg-cyan-500 text-slate-950 shadow-md shadow-cyan-950/40 active:scale-95'
                    }`}
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>{isAr ? 'تشغيل' : 'Execute'}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
