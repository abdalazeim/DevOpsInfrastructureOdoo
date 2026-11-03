import React, { useState } from 'react';
import { 
  X, Globe, Play, Square, RotateCcw, Shield 
} from 'lucide-react';
import { Language, OdooDiscoveryData } from '../types';

interface OdooManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang: Language;
  discovery: OdooDiscoveryData;
  onRefreshDiscovery: () => void;
  onAction: (version: '17' | '18' | '19', action: 'start' | 'stop' | 'restart') => void;
  isOperationRunning: boolean;
}

export const OdooManagerModal: React.FC<OdooManagerModalProps> = ({
  isOpen, onClose, lang, discovery, onRefreshDiscovery, onAction, isOperationRunning
}) => {
  if (!isOpen) return null;
  const isAr = lang === 'ar';

  const renderStatusBadge = (status: string) => {
    const color = status === 'running' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400';
    return <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${color}`}>{status}</span>
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Globe className="w-5 h-5 text-indigo-400" />
            {isAr ? 'مركز إدارة Odoo (17 & 18 & 19)' : 'Odoo Infrastructure Management Center'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X /></button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {['17', '18', '19'].map(ver => {
              const status = discovery[`odoo${ver}` as keyof OdooDiscoveryData] as any;
              return (
                <div key={ver} className="bg-slate-800/50 p-5 rounded-xl border border-slate-700 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-slate-100">Odoo {ver}</h3>
                    {status && renderStatusBadge(status.container_status)}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="text-slate-400">Image:</div>
                    <div className="text-slate-200 truncate">{status?.image || 'N/A'}</div>
                    <div className="text-slate-400">Uptime:</div>
                    <div className="text-slate-200">{status?.uptime || 'N/A'}</div>
                  </div>

                  <div className="flex gap-2">
                    <button onClick={() => onAction(ver as '17'|'18'|'19', 'start')} disabled={isOperationRunning} className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-xs rounded text-white font-bold font-mono">Start</button>
                    <button onClick={() => onAction(ver as '17'|'18'|'19', 'stop')} disabled={isOperationRunning} className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 text-xs rounded text-white font-bold font-mono">Stop</button>
                    <button onClick={() => onAction(ver as '17'|'18'|'19', 'restart')} disabled={isOperationRunning} className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 text-xs rounded text-white font-bold font-mono">Restart</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
