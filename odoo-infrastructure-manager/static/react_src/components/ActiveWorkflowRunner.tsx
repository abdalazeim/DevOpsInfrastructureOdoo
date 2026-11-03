import React from 'react';
import { 
  Play, Pause, XCircle, CheckCircle2, AlertCircle, 
  Clock, Terminal, Loader2, RotateCcw, X 
} from 'lucide-react';
import { OperationPlan, Language } from '../types';

interface ActiveWorkflowRunnerProps {
  plan: OperationPlan;
  currentStepIndex: number;
  isRunning: boolean;
  isPaused: boolean;
  elapsedSeconds: number;
  lang: Language;
  onPauseResume: () => void;
  onCancel: () => void;
  onClose: () => void;
}

export const ActiveWorkflowRunner: React.FC<ActiveWorkflowRunnerProps> = ({
  plan,
  currentStepIndex,
  isRunning,
  isPaused,
  elapsedSeconds,
  lang,
  onPauseResume,
  onCancel,
  onClose,
}) => {
  const isAr = lang === 'ar';
  const totalSteps = plan.steps.length;
  const completedSteps = plan.steps.filter((s) => s.status === 'success').length;
  const hasFailed = plan.steps.some((s) => s.status === 'failed');
  const isComplete = !isRunning && (completedSteps === totalSteps || hasFailed);

  const progressPercent = Math.min(100, Math.round(((completedSteps + (isRunning && !isPaused ? 0.5 : 0)) / totalSteps) * 100));

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = (secs % 60).toFixed(1);
    return `${m.toString().padStart(2, '0')}:${parseFloat(s) < 10 ? '0' : ''}${s}s`;
  };

  return (
    <div className="bg-slate-900 border border-cyan-500/40 rounded-2xl p-5 shadow-2xl relative overflow-hidden backdrop-blur-md">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              {plan.dryRun ? (isAr ? 'معاينة DRY-RUN' : 'DRY-RUN SIMULATION') : (isAr ? 'تنفيذ مباشر LIVE' : 'LIVE EXECUTION')}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ID: {plan.id}
            </span>
          </div>
          <h2 className="text-base font-bold text-slate-100 mt-1">
            {isAr ? plan.name_ar : plan.name}
          </h2>
        </div>

        {/* Status & Timing */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-xs font-mono text-slate-200">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>{formatTime(elapsedSeconds)}</span>
          </div>

          {isRunning && (
            <button
              onClick={onPauseResume}
              className={`p-2 rounded-xl text-xs font-mono flex items-center gap-1.5 border transition-colors ${
                isPaused
                  ? 'bg-amber-950 border-amber-600 text-amber-300'
                  : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
              }`}
            >
              {isPaused ? <Play className="w-3.5 h-3.5 fill-current" /> : <Pause className="w-3.5 h-3.5 fill-current" />}
              <span>{isPaused ? (isAr ? 'استئناف' : 'Resume') : (isAr ? 'إيقاف مؤقت' : 'Pause')}</span>
            </button>
          )}

          {isRunning && (
            <button
              onClick={onCancel}
              className="p-2 rounded-xl text-xs font-mono bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 transition-colors flex items-center gap-1.5"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>{isAr ? 'إلغاء' : 'Cancel'}</span>
            </button>
          )}

          {isComplete && (
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-xs font-mono bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
          <span>{isAr ? `المرحلة ${Math.min(currentStepIndex + 1, totalSteps)} من ${totalSteps}` : `Step ${Math.min(currentStepIndex + 1, totalSteps)} of ${totalSteps}`}</span>
          <span className="text-cyan-400 font-bold">{progressPercent}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              hasFailed
                ? 'bg-rose-500'
                : 'bg-gradient-to-r from-cyan-500 via-indigo-500 to-emerald-400'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Steps Pipeline */}
      <div className="mt-5 space-y-2.5">
        {plan.steps.map((step, idx) => {
          const isCurrent = isRunning && idx === currentStepIndex;
          const isDone = step.status === 'success';
          const isFailed = step.status === 'failed';

          return (
            <div
              key={step.id}
              className={`flex items-start justify-between gap-3 p-3 rounded-xl border text-xs transition-all ${
                isCurrent
                  ? 'bg-cyan-950/30 border-cyan-500/60 shadow-md shadow-cyan-950/20'
                  : isDone
                  ? 'bg-slate-800/40 border-emerald-900/40 text-slate-300'
                  : isFailed
                  ? 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                  : 'bg-slate-800/20 border-slate-800 text-slate-500'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                  {isFailed && <AlertCircle className="w-4 h-4 text-rose-400" />}
                  {isCurrent && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />}
                  {!isDone && !isFailed && !isCurrent && (
                    <span className="w-4 h-4 rounded-full border border-slate-600 flex items-center justify-center text-[9px] font-mono text-slate-500">
                      {idx + 1}
                    </span>
                  )}
                </div>

                <div>
                  <div className={`font-semibold ${isCurrent ? 'text-cyan-300' : isDone ? 'text-slate-200' : 'text-slate-400'}`}>
                    {isAr ? step.name_ar : step.name}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5 font-mono">
                    {step.command.join(' ')}
                  </div>
                </div>
              </div>

              <div className="text-right font-mono text-[11px] shrink-0">
                {step.duration !== undefined && (
                  <span className="text-slate-400">{step.duration.toFixed(1)}s</span>
                )}
                {isCurrent && (
                  <span className="text-cyan-400 animate-pulse block font-bold">
                    {isPaused ? (isAr ? 'موقوف' : 'PAUSED') : (isAr ? 'جارٍ التشغيل...' : 'RUNNING...')}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Completion Banner */}
      {isComplete && (
        <div className={`mt-5 p-3.5 rounded-xl border flex items-center justify-between ${
          hasFailed
            ? 'bg-rose-950/70 border-rose-700 text-rose-200'
            : 'bg-emerald-950/70 border-emerald-700 text-emerald-200'
        }`}>
          <div className="flex items-center gap-2.5">
            {hasFailed ? <AlertCircle className="w-5 h-5 text-rose-400" /> : <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
            <div>
              <div className="font-bold text-sm">
                {hasFailed
                  ? (isAr ? 'فشلت العملية أثناء التنفيذ' : 'Operation Terminated with Errors')
                  : (isAr ? 'تمت العملية بنجاح تام وتم التحقق من الخدمات!' : 'Operation Completed & Verified Successfully!')}
              </div>
              <div className="text-xs opacity-80 font-mono">
                {isAr
                  ? `الوقت الإجمالي: ${formatTime(elapsedSeconds)} • الحاويات تم فحصها`
                  : `Total Elapsed: ${formatTime(elapsedSeconds)} • Containers Verified`}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono hover:bg-slate-800 transition-colors"
          >
            {isAr ? 'إغلاق' : 'Dismiss'}
          </button>
        </div>
      )}
    </div>
  );
};
