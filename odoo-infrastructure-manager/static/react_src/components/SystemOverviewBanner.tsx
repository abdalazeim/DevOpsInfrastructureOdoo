import React, { useState } from 'react';
import { Sparkles, Terminal, CheckCircle2, ChevronDown, ChevronUp, Server, Shield, Database, Cpu } from 'lucide-react';
import { Language } from '../types';

interface SystemOverviewBannerProps {
  lang: Language;
}

export const SystemOverviewBanner: React.FC<SystemOverviewBannerProps> = ({ lang }) => {
  const isAr = lang === 'ar';
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-2xl p-5 shadow-xl shadow-indigo-950/20 relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute -top-12 -right-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header of the Banner */}
      <div className="flex items-center justify-between gap-3 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>{isAr ? 'وصف النظام: Odoo Infrastructure Manager' : 'System Overview: Odoo Infrastructure Manager'}</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                Ubuntu 22.04+ (Server & Desktop)
              </span>
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              {isAr ? 'أداة احترافية لأتمتة بنية أودو وتجهيز الخوادم' : 'Professional multi-version Odoo automation & orchestration engine'}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800/80 transition-colors"
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Body Content */}
      {isExpanded && (
        <div className="mt-4 pt-3.5 border-t border-slate-800/80 space-y-4 relative z-10">
          {/* Official Description Text */}
          <div className="text-sm leading-relaxed text-slate-200/90 bg-slate-950/50 p-4 rounded-xl border border-slate-800/70 font-sans">
            {isAr ? (
              <p>
                نظام <strong className="text-cyan-300">Odoo Infrastructure Manager</strong> هو أداة احترافية لأتمتة إعداد وإدارة بيئات Odoo باستخدام Docker وTraefik، بواجهة Terminal تفاعلية سهلة الاستخدام.
                <br className="my-1" />
                يدعم <strong className="text-indigo-300">جميع إصدارات Ubuntu Server وUbuntu Desktop</strong> بدءًا من <span className="font-mono text-emerald-400">Ubuntu 22.04 LTS وحتى أحدث إصدار مستقر</span>، مع إمكانية إدارة <strong className="text-cyan-300">Odoo 17 وOdoo 18 وOdoo 19</strong> وقواعد بيانات <strong className="text-emerald-300">PostgreSQL</strong> و<strong className="text-cyan-300">pgAdmin</strong>، وتخصيص إعدادات الخادم والشبكات والنطاقات والتخزين في كل تجربة.
                <br className="my-1" />
                يوفر النظام التثبيت والإعداد التلقائي، ومراقبة الخدمات، وإدارة السجلات، والنسخ الاحتياطي والاستعادة، مع حفظ ملفات الإعداد وإمكانية إعادة تنفيذ العمليات بأمان.
              </p>
            ) : (
              <p>
                The <strong className="text-cyan-300">Odoo Infrastructure Manager</strong> is a professional tool for automating the provisioning and management of Odoo environments using Docker and Traefik, featuring an intuitive interactive Terminal interface.
                <br className="my-1" />
                It supports <strong className="text-indigo-300">all Ubuntu Server and Ubuntu Desktop editions</strong> starting from <span className="font-mono text-emerald-400">Ubuntu 22.04 LTS up to the latest stable release</span>, enabling simultaneous management of <strong className="text-cyan-300">Odoo 17, Odoo 18 & Odoo 19</strong> alongside isolated <strong className="text-emerald-300">PostgreSQL</strong> databases and <strong className="text-cyan-300">pgAdmin</strong>, with customized server, network, domain, and persistent storage configurations per experiment.
                <br className="my-1" />
                The system provides automated installation, baseline configuration, live service monitoring, log streaming, and verified backup/restore workflows with profile persistence and safe execution safeguards.
              </p>
            )}
          </div>

          {/* Quick Feature Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400 shrink-0" />
              <div>
                <div className="text-slate-200 font-semibold">{isAr ? 'خوادم وأجهزة أوبونتو' : 'Ubuntu Server & Desktop'}</div>
                <div className="text-[11px] text-slate-400">22.04 LTS ➔ Latest</div>
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-400 shrink-0" />
              <div>
                <div className="text-slate-200 font-semibold">Traefik v3.7 Ingress</div>
                <div className="text-[11px] text-slate-400">ACME TLS & Redirection</div>
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 flex items-center gap-2">
              <Database className="w-4 h-4 text-emerald-400 shrink-0" />
              <div>
                <div className="text-slate-200 font-semibold">{isAr ? 'عزل PostgreSQL' : 'PG 16 / 17 / 18 Isolated'}</div>
                <div className="text-[11px] text-slate-400">{isAr ? 'شبكة داخلية خاصة' : 'Internal Bridge Only'}</div>
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-purple-400 shrink-0" />
              <div>
                <div className="text-slate-200 font-semibold">{isAr ? 'واجهة Terminal وتأمين' : 'TUI & Dry-Run Safe'}</div>
                <div className="text-[11px] text-slate-400">{isAr ? 'حماية من فقدان البيانات' : 'Pre-restore Safety Guard'}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
