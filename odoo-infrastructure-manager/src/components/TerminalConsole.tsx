import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, Download, Copy, Trash2, Search, 
  ArrowDownCircle, PauseCircle, PlayCircle, Check, Maximize2, Minimize2 
} from 'lucide-react';
import { Language } from '../types';

interface TerminalConsoleProps {
  logs: string[];
  lang: Language;
  onClearLogs: () => void;
  hostname: string;
}

export const TerminalConsole: React.FC<TerminalConsoleProps> = ({
  logs,
  lang,
  onClearLogs,
  hostname,
}) => {
  const isAr = lang === 'ar';
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [filterText, setFilterText] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadLogs = () => {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `odoo-manager-${hostname}-${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = filterText.trim()
    ? logs.filter((line) => line.toLowerCase().includes(filterText.toLowerCase()))
    : logs;

  // Format line with ANSI style colors
  const formatLogLine = (line: string, index: number) => {
    let colorClass = 'text-slate-300';

    if (line.includes('[OK]') || line.includes('✔') || line.includes('succeeded') || line.includes('healthy')) {
      colorClass = 'text-emerald-400 font-medium';
    } else if (line.includes('CRITICAL')) {
      colorClass = 'text-rose-600 font-bold bg-rose-950/20';
    } else if (line.includes('ERROR')) {
      colorClass = 'text-rose-400 font-bold';
    } else if (line.includes('WARNING')) {
      colorClass = 'text-amber-300';
    } else if (line.includes('INFO') || line.includes('==>')) {
      colorClass = 'text-cyan-300';
    } else if (line.includes('[DRY-RUN]')) {
      colorClass = 'text-purple-300 font-semibold';
    } else if (line.startsWith('#') || line.includes('====')) {
      colorClass = 'text-slate-500 font-bold';
    }

    return (
      <div key={index} className={`font-mono text-[12px] leading-5 whitespace-pre-wrap break-all ${colorClass}`}>
        {line}
      </div>
    );
  };

  return (
    <div
      className={`bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl flex flex-col transition-all overflow-hidden ${
        isFullScreen ? 'fixed inset-4 z-50 shadow-[0_0_50px_rgba(0,0,0,0.8)]' : 'h-[440px]'
      }`}
    >
      {/* Terminal Title Bar */}
      <div className="bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          {/* Window control dots */}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-rose-500/80 border border-rose-600 inline-block" />
            <span className="w-3 h-3 rounded-full bg-amber-500/80 border border-amber-600 inline-block" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 border border-emerald-600 inline-block" />
          </div>

          <div className="flex items-center gap-1.5 ml-3 text-xs font-mono text-slate-300">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>root@{hostname}:/opt/odoo-infrastructure-manager#</span>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-2">
          {/* Search Filter */}
          <div className="relative hidden sm:block">
            <Search className="w-3 h-3 text-slate-400 absolute left-2 top-2 pointer-events-none" />
            <input
              type="text"
              placeholder={isAr ? 'بحث في السجلات...' : 'Filter output...'}
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-md pl-7 pr-2 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-36 font-mono"
            />
          </div>

          {/* Auto-Scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-mono border transition-colors ${
              autoScroll
                ? 'bg-cyan-950/80 border-cyan-700 text-cyan-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
            title={autoScroll ? (isAr ? 'إيقاف التمرير التلقائي' : 'Pause autoscroll') : (isAr ? 'تشغيل التمرير التلقائي' : 'Resume autoscroll')}
          >
            {autoScroll ? <PauseCircle className="w-3 h-3" /> : <PlayCircle className="w-3 h-3" />}
            <span className="hidden md:inline">{autoScroll ? 'Autoscroll' : 'Paused'}</span>
          </button>

          {/* Copy Button */}
          <button
            onClick={handleCopyLogs}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title={isAr ? 'نسخ السجلات للحافظة' : 'Copy logs to clipboard'}
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownloadLogs}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title={isAr ? 'تحميل ملف السجل .log' : 'Download log file'}
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          {/* Clear Button */}
          <button
            onClick={onClearLogs}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors"
            title={isAr ? 'مسح الشاشة' : 'Clear console'}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullScreen(!isFullScreen)}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title={isFullScreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullScreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Terminal Screen Body */}
      <div className="flex-1 p-4 overflow-y-auto font-mono selection:bg-cyan-900 selection:text-cyan-100 bg-slate-950/95 space-y-0.5">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-600 text-xs py-8 text-center select-none font-mono">
            {filterText
              ? (isAr ? 'لا توجد أسطر تطابق نص البحث.' : 'No log lines match current filter.')
              : (isAr ? 'لا توجد سجلات بعد. اختر عملية من القائمة للبدء.' : 'Terminal ready. Execute a workflow or health check to stream logs.')}
          </div>
        ) : (
          filteredLogs.map((line, idx) => formatLogLine(line, idx))
        )}

        {/* Cursor Indicator */}
        <div className="flex items-center gap-2 pt-2 text-cyan-400 text-xs font-mono select-none">
          <span>root@{hostname}:~#</span>
          <span className="w-2 h-4 bg-cyan-400 animate-pulse inline-block" />
        </div>

        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};
