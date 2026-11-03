import React, { useState } from 'react';
import { 
  X, Check, AlertTriangle, Sliders, FileText, 
  Shield, Server, Globe, Database, HardDrive, Eye, EyeOff, Copy 
} from 'lucide-react';
import { InfrastructureProfile, Language } from '../types';

interface ProfileEditorModalProps {
  profile: InfrastructureProfile;
  lang: Language;
  onSave: (updated: InfrastructureProfile) => void;
  onClose: () => void;
}

export const ProfileEditorModal: React.FC<ProfileEditorModalProps> = ({
  profile,
  lang,
  onSave,
  onClose,
}) => {
  const isAr = lang === 'ar';
  const [activeTab, setActiveTab] = useState<'visual' | 'yaml'>('visual');
  const [edited, setEdited] = useState<InfrastructureProfile>(JSON.parse(JSON.stringify(profile)));
  const [showSecrets, setShowSecrets] = useState<boolean>(false);

  // Real-time validation
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!edited.server.hostname) errors.push(isAr ? 'اسم الخادم لا يمكن أن يكون فارغاً' : 'Server hostname cannot be empty');
  if (edited.paths.data_root === '/' || edited.paths.data_root === '/etc') {
    errors.push(isAr ? 'تحذير أمني خطير: لا يمكن استخدام جذر النظام كمجلد للبيانات' : 'Critical security alert: data_root cannot be root filesystem directory');
  }
  if (edited.traefik.http_port === edited.traefik.https_port) {
    errors.push(isAr ? 'تعارض في منافذ ترافيك: منفذ HTTP يطابق HTTPS' : 'Port collision: HTTP port matches HTTPS port');
  }
  if (edited.odoo17.domain === edited.traefik.dashboard_domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 17 يطابق نطاق لوحة تحكم ترافيك' : 'Domain collision: Odoo 17 domain matches Traefik dashboard');
  }
  if (edited.odoo18.domain === edited.odoo17.domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 18 يطابق نطاق Odoo 17' : 'Domain collision: Odoo 18 domain matches Odoo 17 domain');
  }
  if (edited.odoo18.domain === edited.traefik.dashboard_domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 18 يطابق نطاق لوحة تحكم ترافيك' : 'Domain collision: Odoo 18 domain matches Traefik dashboard');
  }
  if (edited.odoo19.domain === edited.odoo17.domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 19 يطابق نطاق Odoo 17' : 'Domain collision: Odoo 19 domain matches Odoo 17 domain');
  }
  if (edited.odoo19.domain === edited.odoo18.domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 19 يطابق نطاق Odoo 18' : 'Domain collision: Odoo 19 domain matches Odoo 18 domain');
  }
  if (edited.odoo19.domain === edited.traefik.dashboard_domain) {
    errors.push(isAr ? 'تعارض نطاق: نطاق Odoo 19 يطابق نطاق لوحة تحكم ترافيك' : 'Domain collision: Odoo 19 domain matches Traefik dashboard');
  }
  if (edited.backup.retention_count < 1) {
    errors.push(isAr ? 'عدد النسخ المحفوظة يجب أن يكون 1 على الأقل' : 'Backup retention count must be at least 1');
  }

  // Engine warning check
  if (edited.odoo17.database.engine.includes('18')) {
    warnings.push(isAr ? 'Odoo 17 مختبر رسمياً مع بوستجريس 13-16، المحرك المحدد قد يتطلب اختبارات توافق' : 'Odoo 17 is officially tested on PG 13-16. Verify engine compatibility.');
  }
  if (edited.odoo18.database.engine.includes('18')) {
    warnings.push(isAr ? 'Odoo 18 يستهدف PostgreSQL 15-17 رسمياً، المحرك المحدد قد يتطلب اختبارات توافق' : 'Odoo 18 officially targets PostgreSQL 15-17. Verify engine compatibility.');
  }
  if (!edited.odoo19.database.engine.includes('18')) {
    warnings.push(isAr ? 'Odoo 19 يستهدف PostgreSQL 18 رسمياً، راجع محرك القاعدة المحدد' : 'Odoo 19 officially targets PostgreSQL 18. Review the selected database engine.');
  }

  const generateYamlPreview = () => {
    return `# Odoo Infrastructure Profile
profile_name: "${edited.profile_name}"
description: "${edited.description}"
version: "${edited.version}"

server:
  hostname: "${edited.server.hostname}"
  ip_or_host: "${edited.server.ip_or_host}"
  timezone: "${edited.server.timezone}"
  ssh_user: "${edited.server.ssh_user}"
  ssh_port: ${edited.server.ssh_port}

paths:
  data_root: "${edited.paths.data_root}"
  backup_root: "${edited.paths.backup_root}"

network:
  proxy_network_name: "${edited.network.proxy_network_name}"
  proxy_subnet: "${edited.network.proxy_subnet}"

traefik:
  enabled: ${edited.traefik.enabled}
  image: "${edited.traefik.image}"
  dashboard_domain: "${edited.traefik.dashboard_domain}"
  acme_email: "${edited.traefik.acme_email}"
  http_port: ${edited.traefik.http_port}
  https_port: ${edited.traefik.https_port}

odoo17:
  enabled: ${edited.odoo17.enabled}
  domain: "${edited.odoo17.domain}"
  image: "${edited.odoo17.image}"
  workers: ${edited.odoo17.workers}
  database:
    engine: "${edited.odoo17.database.engine}"
    name: "${edited.odoo17.database.name}"
    user: "${edited.odoo17.database.user}"
    password_env_var: "${edited.odoo17.database.password_env_var}"

odoo18:
  enabled: ${edited.odoo18.enabled}
  domain: "${edited.odoo18.domain}"
  image: "${edited.odoo18.image}"
  workers: ${edited.odoo18.workers}
  database:
    engine: "${edited.odoo18.database.engine}"
    name: "${edited.odoo18.database.name}"
    user: "${edited.odoo18.database.user}"
    password_env_var: "${edited.odoo18.database.password_env_var}"

odoo19:
  enabled: ${edited.odoo19.enabled}
  domain: "${edited.odoo19.domain}"
  image: "${edited.odoo19.image}"
  workers: ${edited.odoo19.workers}
  database:
    engine: "${edited.odoo19.database.engine}"
    name: "${edited.odoo19.database.name}"
    user: "${edited.odoo19.database.user}"
    password_env_var: "${edited.odoo19.database.password_env_var}"

backup:
  enabled: ${edited.backup.enabled}
  cron_schedule: "${edited.backup.cron_schedule}"
  retention_count: ${edited.backup.retention_count}
  include_filestore: ${edited.backup.include_filestore}
`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                {isAr ? 'محرر ملف الإعداد والتحقق من التوافق' : 'Profile Configuration & Compatibility Editor'}
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                {edited.profile_name} • {edited.server.hostname}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-800 p-0.5 rounded-lg border border-slate-700">
              <button
                onClick={() => setActiveTab('visual')}
                className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                  activeTab === 'visual' ? 'bg-cyan-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'النموذج التفاعلي' : 'Visual Form'}
              </button>
              <button
                onClick={() => setActiveTab('yaml')}
                className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                  activeTab === 'yaml' ? 'bg-cyan-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'معاينة YAML' : 'YAML Preview'}
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Validation Banners */}
        {errors.length > 0 && (
          <div className="bg-rose-950/80 border-b border-rose-800 px-6 py-2.5 text-xs text-rose-300 font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <div>
              <span className="font-bold">{isAr ? 'أخطاء التكوين:' : 'Configuration Errors:'}</span> {errors.join(' • ')}
            </div>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="bg-amber-950/80 border-b border-amber-800 px-6 py-2 text-xs text-amber-300 font-mono flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
            <div>{warnings.join(' • ')}</div>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {activeTab === 'visual' ? (
            <div className="space-y-6 text-xs">
              
              {/* Server & Network Group */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 space-y-3">
                <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2 text-cyan-400">
                  <Server className="w-4 h-4" />
                  {isAr ? 'إعدادات الخادم والشبكة' : 'Server & Network Settings'}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'اسم الخادم (Hostname)' : 'Hostname'}</label>
                    <input
                      type="text"
                      value={edited.server.hostname}
                      onChange={(e) => setEdited({ ...edited, server: { ...edited.server, hostname: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'عنوان IP أو المضيف' : 'IP / Host'}</label>
                    <input
                      type="text"
                      value={edited.server.ip_or_host}
                      onChange={(e) => setEdited({ ...edited, server: { ...edited.server, ip_or_host: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'المنطقة الزمنية' : 'Timezone'}</label>
                    <input
                      type="text"
                      value={edited.server.timezone}
                      onChange={(e) => setEdited({ ...edited, server: { ...edited.server, timezone: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'شبكة البروكسي المشتركة' : 'Proxy Network'}</label>
                    <input
                      type="text"
                      value={edited.network.proxy_network_name}
                      onChange={(e) => setEdited({ ...edited, network: { ...edited.network, proxy_network_name: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Traefik & SSL Group */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 space-y-3">
                <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2 text-cyan-400">
                  <Shield className="w-4 h-4" />
                  {isAr ? 'إعدادات موجه ترافيك وشهادات SSL' : 'Traefik v3.7 & TLS Configuration'}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'نطاق لوحة التحكم' : 'Dashboard Domain'}</label>
                    <input
                      type="text"
                      value={edited.traefik.dashboard_domain}
                      onChange={(e) => setEdited({ ...edited, traefik: { ...edited.traefik, dashboard_domain: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'بريد Let\'s Encrypt' : 'ACME Email'}</label>
                    <input
                      type="email"
                      value={edited.traefik.acme_email}
                      onChange={(e) => setEdited({ ...edited, traefik: { ...edited.traefik, acme_email: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-3 pt-6">
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={edited.traefik.enabled}
                        onChange={(e) => setEdited({ ...edited, traefik: { ...edited.traefik, enabled: e.target.checked } })}
                        className="rounded border-slate-700 text-cyan-500 focus:ring-0"
                      />
                      <span>{isAr ? 'تفعيل Traefik v3.7' : 'Enable Traefik v3.7'}</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Odoo 17 / 18 / 19 Instances */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                
                {/* Odoo 17 */}
                <div className="bg-slate-800/40 border border-indigo-500/30 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
                    <h4 className="font-bold text-indigo-300 flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Odoo 17.0
                    </h4>
                    <span className="text-[10px] font-mono bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800">
                      PostgreSQL 16
                    </span>
                  </div>
                  <div className="space-y-2.5">
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'النطاق (Domain)' : 'Domain'}</label>
                      <input
                        type="text"
                        value={edited.odoo17.domain}
                        onChange={(e) => setEdited({ ...edited, odoo17: { ...edited.odoo17, domain: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'صورة الحاوية' : 'Docker Image'}</label>
                      <input
                        type="text"
                        value={edited.odoo17.image}
                        onChange={(e) => setEdited({ ...edited, odoo17: { ...edited.odoo17, image: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'اسم القاعدة' : 'DB Name'}</label>
                        <input
                          type="text"
                          value={edited.odoo17.database.name}
                          onChange={(e) => setEdited({ ...edited, odoo17: { ...edited.odoo17, database: { ...edited.odoo17.database, name: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'محرك القاعدة' : 'DB Engine'}</label>
                        <input
                          type="text"
                          value={edited.odoo17.database.engine}
                          onChange={(e) => setEdited({ ...edited, odoo17: { ...edited.odoo17, database: { ...edited.odoo17.database, engine: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Odoo 18 */}
                <div className="bg-slate-800/40 border border-emerald-500/30 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
                    <h4 className="font-bold text-emerald-300 flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Odoo 18.0
                    </h4>
                    <span className="text-[10px] font-mono bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-800">
                      PostgreSQL 17
                    </span>
                  </div>
                  <div className="space-y-2.5">
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'النطاق (Domain)' : 'Domain'}</label>
                      <input
                        type="text"
                        value={edited.odoo18.domain}
                        onChange={(e) => setEdited({ ...edited, odoo18: { ...edited.odoo18, domain: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'صورة الحاوية' : 'Docker Image'}</label>
                      <input
                        type="text"
                        value={edited.odoo18.image}
                        onChange={(e) => setEdited({ ...edited, odoo18: { ...edited.odoo18, image: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'اسم القاعدة' : 'DB Name'}</label>
                        <input
                          type="text"
                          value={edited.odoo18.database.name}
                          onChange={(e) => setEdited({ ...edited, odoo18: { ...edited.odoo18, database: { ...edited.odoo18.database, name: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-emerald-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'محرك القاعدة' : 'DB Engine'}</label>
                        <input
                          type="text"
                          value={edited.odoo18.database.engine}
                          onChange={(e) => setEdited({ ...edited, odoo18: { ...edited.odoo18, database: { ...edited.odoo18.database, engine: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-emerald-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Odoo 19 */}
                <div className="bg-slate-800/40 border border-purple-500/30 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
                    <h4 className="font-bold text-purple-300 flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Odoo 19.0
                    </h4>
                    <span className="text-[10px] font-mono bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800">
                      PostgreSQL 18
                    </span>
                  </div>
                  <div className="space-y-2.5">
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'النطاق (Domain)' : 'Domain'}</label>
                      <input
                        type="text"
                        value={edited.odoo19.domain}
                        onChange={(e) => setEdited({ ...edited, odoo19: { ...edited.odoo19, domain: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-purple-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'صورة الحاوية' : 'Docker Image'}</label>
                      <input
                        type="text"
                        value={edited.odoo19.image}
                        onChange={(e) => setEdited({ ...edited, odoo19: { ...edited.odoo19, image: e.target.value } })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-purple-500 focus:outline-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'اسم القاعدة' : 'DB Name'}</label>
                        <input
                          type="text"
                          value={edited.odoo19.database.name}
                          onChange={(e) => setEdited({ ...edited, odoo19: { ...edited.odoo19, database: { ...edited.odoo19.database, name: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-purple-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-slate-400 block mb-0.5 font-mono">{isAr ? 'محرك القاعدة' : 'DB Engine'}</label>
                        <input
                          type="text"
                          value={edited.odoo19.database.engine}
                          onChange={(e) => setEdited({ ...edited, odoo19: { ...edited.odoo19, database: { ...edited.odoo19.database, engine: e.target.value } } })}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono focus:border-purple-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              {/* Backup & Retention Policy */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 space-y-3">
                <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2 text-cyan-400">
                  <Database className="w-4 h-4" />
                  {isAr ? 'سياسة النسخ الاحتياطي والاحتفاظ (Retention Policy)' : 'Backup & Retention Policy'}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'جدول كرون (Cron Expression)' : 'Cron Schedule'}</label>
                    <input
                      type="text"
                      value={edited.backup.cron_schedule}
                      onChange={(e) => setEdited({ ...edited, backup: { ...edited.backup, cron_schedule: e.target.value } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">{isAr ? 'عدد النسخ المحفوظة (Retention Count)' : 'Retention Count'}</label>
                    <input
                      type="number"
                      min={1}
                      max={60}
                      value={edited.backup.retention_count}
                      onChange={(e) => setEdited({ ...edited, backup: { ...edited.backup, retention_count: parseInt(e.target.value) || 1 } })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-3 pt-6">
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={edited.backup.include_filestore}
                        onChange={(e) => setEdited({ ...edited, backup: { ...edited.backup, include_filestore: e.target.checked } })}
                        className="rounded border-slate-700 text-cyan-500 focus:ring-0"
                      />
                      <span>{isAr ? 'أرشفة المرفقات (Filestore)' : 'Include Filestore Archive'}</span>
                    </label>
                  </div>
                </div>
              </div>

            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-mono text-slate-400">{isAr ? 'معاينة YAML التلقائية المقابلة للتكوين' : 'Generated YAML Equivalent Preview'}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(generateYamlPreview())}
                  className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-mono"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>{isAr ? 'نسخ YAML' : 'Copy YAML'}</span>
                </button>
              </div>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed">
                {generateYamlPreview()}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="bg-slate-950 px-6 py-4 border-t border-slate-800 flex items-center justify-between">
          <div className="text-xs font-mono text-slate-400">
            {errors.length === 0 ? (
              <span className="text-emerald-400 flex items-center gap-1.5 font-bold">
                <Check className="w-4 h-4" />
                {isAr ? 'الملف سليم وقابل للتنفيذ' : 'Profile syntax verified and ready'}
              </span>
            ) : (
              <span className="text-rose-400 font-bold">
                {errors.length} {isAr ? 'أخطاء بحاجة للإصلاح' : 'errors must be resolved'}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition-colors"
            >
              {isAr ? 'إلغاء' : 'Cancel'}
            </button>
            <button
              disabled={errors.length > 0}
              onClick={() => {
                onSave(edited);
                onClose();
              }}
              className={`px-4 py-2 rounded-xl text-xs font-bold font-mono transition-all flex items-center gap-1.5 ${
                errors.length > 0
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-950/40'
              }`}
            >
              <Check className="w-4 h-4 stroke-[3]" />
              <span>{isAr ? 'حفظ وتطبيق الإعدادات' : 'Save & Apply Profile'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
