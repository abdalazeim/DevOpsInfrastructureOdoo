import React, { useState } from 'react';
import { 
  X, Database, Download, RotateCcw, Shield, 
  AlertTriangle, CheckCircle2, Copy, Check, FileArchive, HardDrive 
} from 'lucide-react';
import { BackupMetadata, InfrastructureProfile, Language } from '../types';

interface DatabaseManagerModalProps {
  profile: InfrastructureProfile;
  backups: BackupMetadata[];
  lang: Language;
  onTakeBackup: (version: '17' | '18' | '19', dbName: string) => void;
  onTriggerRestore: (version: '17' | '18' | '19', dumpFile: string, targetDb: string) => void;
  onClose: () => void;
}

export const DatabaseManagerModal: React.FC<DatabaseManagerModalProps> = ({
  profile,
  backups,
  lang,
  onTakeBackup,
  onTriggerRestore,
  onClose,
}) => {
  const isAr = lang === 'ar';
  const [activeTab, setActiveTab] = useState<'catalog' | 'restore'>('catalog');
  const [selectedVersion, setSelectedVersion] = useState<'17' | '18' | '19'>('17');
  const [targetDbName, setTargetDbName] = useState<string>(profile.odoo17.database.name);
  const [selectedDumpFile, setSelectedDumpFile] = useState<string>(backups[0]?.dump_file || '');
  const [confirmationToken, setConfirmationToken] = useState<string>('');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const expectedToken = `RESTORE-${targetDbName}`;
  const isConfirmationValid = confirmationToken.trim() === expectedToken;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                {isAr ? 'مركز إدارة قواعد بيانات أودو والنسخ الاحتياطي' : 'PostgreSQL Database & Backup Recovery Center'}
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                PostgreSQL 16 (Odoo 17) • PostgreSQL 17 (Odoo 18) • PostgreSQL 18 (Odoo 19) • Filestore Snapshots
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-800 p-0.5 rounded-lg border border-slate-700">
              <button
                onClick={() => setActiveTab('catalog')}
                className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                  activeTab === 'catalog' ? 'bg-cyan-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'سجل النسخ الاحتياطية' : 'Backup Snapshots'}
              </button>
              <button
                onClick={() => setActiveTab('restore')}
                className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                  activeTab === 'restore' ? 'bg-rose-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'الاستعادة الآمنة' : 'Safe Restore'}
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

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {activeTab === 'catalog' ? (
            <div className="space-y-6">
              
              {/* Trigger Instant Backup Card */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <Download className="w-4 h-4 text-cyan-400" />
                    {isAr ? 'توليد نسخة احتياطية فورية' : 'Trigger Immediate Backup'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {isAr
                      ? 'يتم تفريغ قاعدة البيانات عبر pg_dump وأرشفة مرفقات Odoo filestore مع التحقق من SHA256'
                      : 'Executes pg_dump, archives filestore, generates SHA256 checksum, and enforces retention.'}
                  </p>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <select
                    value={selectedVersion}
                    onChange={(e) => {
                      const v = e.target.value as '17' | '18' | '19';
                      setSelectedVersion(v);
                      setTargetDbName(
                        v === '17' ? profile.odoo17.database.name
                          : v === '18' ? profile.odoo18.database.name
                          : profile.odoo19.database.name
                      );
                    }}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none"
                  >
                    <option value="17">Odoo 17 (PG 16)</option>
                    <option value="18">Odoo 18 (PG 17)</option>
                    <option value="19">Odoo 19 (PG 18)</option>
                  </select>

                  <button
                    onClick={() => {
                      onTakeBackup(selectedVersion, targetDbName);
                      onClose();
                    }}
                    className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs font-mono shadow-md shadow-cyan-950/40 flex items-center gap-1.5 whitespace-nowrap"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>{isAr ? 'أخذ النسخة الآن' : 'Backup Now'}</span>
                  </button>
                </div>
              </div>

              {/* Backups Table */}
              <div>
                <h4 className="text-xs font-mono text-slate-400 mb-2.5 uppercase tracking-wider">
                  {isAr ? 'النسخ المتوفرة على الخادم' : 'Verified Backups in Storage'}
                </h4>
                <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-900 border-b border-slate-800 text-slate-400 font-mono">
                        <th className="py-2.5 px-3">{isAr ? 'الإصدار والقاعدة' : 'Version & DB'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'التاريخ والوقت' : 'Timestamp'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'حجم SQL' : 'Dump Size'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'المرفقات' : 'Filestore'}</th>
                        <th className="py-2.5 px-3">{isAr ? 'بصمة SHA256' : 'SHA256 Checksum'}</th>
                        <th className="py-2.5 px-3 text-right">{isAr ? 'إجراء' : 'Action'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {backups.map((bk) => (
                        <tr key={bk.id} className="hover:bg-slate-900/50 transition-colors">
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                                bk.version === '17'
                                  ? 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                                  : bk.version === '18'
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                    : 'bg-purple-950 text-purple-300 border border-purple-800'
                              }`}>
                                Odoo {bk.version}
                              </span>
                              <span className="font-semibold text-slate-200">{bk.database}</span>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-slate-400">{bk.timestamp}</td>
                          <td className="py-3 px-3 text-cyan-300 font-bold">{formatBytes(bk.dump_size_bytes)}</td>
                          <td className="py-3 px-3">
                            {bk.has_filestore ? (
                              <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                                <FileArchive className="w-3 h-3" />
                                {formatBytes(bk.filestore_size_bytes || 0)}
                              </span>
                            ) : (
                              <span className="text-slate-600">-</span>
                            )}
                          </td>
                          <td className="py-3 px-3">
                            <button
                              onClick={() => handleCopyHash(bk.sha256)}
                              className="flex items-center gap-1 text-slate-400 hover:text-slate-200 text-[11px] font-mono group"
                              title={bk.sha256}
                            >
                              <span>{bk.sha256.substring(0, 12)}...</span>
                              {copiedHash === bk.sha256 ? (
                                <Check className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3 text-slate-600 group-hover:text-slate-400" />
                              )}
                            </button>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => {
                                setSelectedVersion(bk.version);
                                setSelectedDumpFile(bk.dump_file);
                                setTargetDbName(bk.database);
                                setActiveTab('restore');
                              }}
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-rose-950/80 hover:text-rose-300 border border-slate-700 text-slate-300 text-xs font-mono transition-colors"
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
          ) : (
            <div className="space-y-6">
              
              {/* Warning Callout */}
              <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-rose-300 text-sm">
                    {isAr ? 'تحذير أمني شديد: استعادة قاعدة بيانات قائمة' : 'CRITICAL SAFETY GUARD: DATABASE RESTORATION'}
                  </h4>
                  <p className="text-xs text-rose-200/90 mt-1 leading-relaxed">
                    {isAr
                      ? 'عملية الاستعادة ستقوم بإعادة إنشاء الجداول وحذف البيانات السابقة في القاعدة المستهدفة. لضمان عدم فقدان البيانات، يقوم السكربت تلقائياً بأخذ نسخة أمان احتياطية فورية قبل بدء الاستعادة في مجلد safety_pre_restore.'
                      : 'Restoring an archive drops existing tables in the target database. To prevent unrecoverable data loss, an automated pre-restore safety snapshot will be created in safety_pre_restore before any deletion.'}
                  </p>
                </div>
              </div>

              {/* Restore Form */}
              <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-5 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1 font-mono">{isAr ? 'إصدار Odoo المستهدف' : 'Target Odoo Version'}</label>
                    <select
                      value={selectedVersion}
                      onChange={(e) => setSelectedVersion(e.target.value as '17' | '18' | '19')}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    >
                      <option value="17">Odoo 17 (PostgreSQL 16)</option>
                      <option value="18">Odoo 18 (PostgreSQL 17)</option>
                      <option value="19">Odoo 19 (PostgreSQL 18)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 block mb-1 font-mono">{isAr ? 'اسم القاعدة المستهدفة' : 'Target Database Name'}</label>
                    <input
                      type="text"
                      value={targetDbName}
                      onChange={(e) => setTargetDbName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1 font-mono">{isAr ? 'ملف الأرشيف المراد استرجاعه' : 'Selected Archive Dump File'}</label>
                  <select
                    value={selectedDumpFile}
                    onChange={(e) => setSelectedDumpFile(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                  >
                    {backups.map((bk) => (
                      <option key={bk.id} value={bk.dump_file}>
                        {bk.dump_file} ({bk.database} - {bk.timestamp})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Explicit Safety Token Input */}
                <div className="pt-2">
                  <label className="text-xs text-slate-300 block mb-1 font-mono">
                    {isAr ? `للتأكيد، يرجى كتابة رمز الأمان بالضبط: ` : `To confirm, please type the safety phrase exactly: `}
                    <code className="bg-rose-950 text-rose-300 px-1.5 py-0.5 rounded border border-rose-800 font-bold">
                      {expectedToken}
                    </code>
                  </label>
                  <input
                    type="text"
                    placeholder={expectedToken}
                    value={confirmationToken}
                    onChange={(e) => setConfirmationToken(e.target.value)}
                    className="w-full bg-slate-950 border border-rose-800 rounded-lg px-3 py-2 text-xs text-rose-300 font-mono placeholder-slate-700 focus:border-rose-500 focus:outline-none"
                  />
                </div>

                <div className="pt-3 flex justify-end">
                  <button
                    disabled={!isConfirmationValid}
                    onClick={() => {
                      onTriggerRestore(selectedVersion, selectedDumpFile, targetDbName);
                      onClose();
                    }}
                    className={`px-5 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
                      isConfirmationValid
                        ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/40 active:scale-95'
                        : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                    }`}
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>{isAr ? 'تأكيد وبدء الاستعادة الآمنة' : 'Confirm & Execute Safe Restore'}</span>
                  </button>
                </div>
              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-950 px-6 py-3.5 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>{isAr ? 'التخزين: /opt/odoo-infrastructure/backups' : 'Storage Path: /opt/odoo-infrastructure/backups'}</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            {isAr ? 'إغلاق' : 'Close'}
          </button>
        </div>

      </div>
    </div>
  );
};
