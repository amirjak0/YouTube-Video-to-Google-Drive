import React, { useRef, useEffect } from 'react';
import { Terminal, X, StopCircle, CheckCircle2, ArrowUpCircle, AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';
import { SyncJob } from '../types';

interface LiveJobDrawerProps {
  job: SyncJob | null;
  isOpen: boolean;
  onClose: () => void;
  onCancel: (jobId: string) => void;
}

export const LiveJobDrawer: React.FC<LiveJobDrawerProps> = ({
  job,
  isOpen,
  onClose,
  onCancel
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [job?.logs]);

  if (!isOpen || !job) return null;

  const percent = job.totalVideos > 0
    ? Math.round((job.processedVideos / job.totalVideos) * 100)
    : 0;

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 bg-slate-950/95 border-t border-slate-800 shadow-2xl backdrop-blur-xl transition-all duration-300 max-h-[75vh] flex flex-col">
      {/* Header bar */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-slate-800 text-red-400">
            {job.status === 'running' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : job.status === 'completed' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <Terminal className="w-5 h-5 text-slate-400" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">
                Sync Execution Engine — Job {job.id}
              </h3>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                  job.status === 'running'
                    ? 'bg-amber-500/20 text-amber-300 animate-pulse border border-amber-500/30'
                    : job.status === 'completed'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'bg-red-500/20 text-red-300 border border-red-500/30'
                }`}
              >
                {job.status}
              </span>
            </div>
            {job.currentVideoTitle && (
              <p className="text-xs text-slate-400 truncate max-w-lg mt-0.5">
                Current: <span className="text-slate-200">{job.currentVideoTitle}</span>
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {job.status === 'running' && (
            <button
              onClick={() => onCancel(job.id)}
              className="text-xs px-3 py-1.5 rounded-xl bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 transition flex items-center gap-1.5"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Cancel Job</span>
            </button>
          )}

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Progress metrics */}
      <div className="p-4 bg-slate-900/40 border-b border-slate-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex-1 max-w-xl space-y-1.5">
          <div className="flex justify-between text-[11px] text-slate-400">
            <span>Progress: {job.processedVideos} / {job.totalVideos} videos</span>
            <span className="font-mono font-bold text-white">{percent}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-600 via-amber-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>

        <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
          <span className="flex items-center gap-1 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {job.successCount} Synced
          </span>
          <span className="flex items-center gap-1 text-amber-400">
            <ArrowUpCircle className="w-3.5 h-3.5" />
            {job.upgradedCount} Upgraded
          </span>
          <span className="flex items-center gap-1 text-slate-400">
            {job.skippedCount} Skipped (Current)
          </span>
        </div>
      </div>

      {/* Terminal logs view */}
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 bg-black/70 select-text"
        style={{ minHeight: '180px', maxHeight: '350px' }}
      >
        {job.logs.map((log, idx) => {
          let color = 'text-slate-300';
          if (log.level === 'success') color = 'text-emerald-400';
          if (log.level === 'warn') color = 'text-amber-400 font-medium';
          if (log.level === 'error') color = 'text-red-400 font-bold';

          return (
            <div key={idx} className="flex items-start gap-2 leading-relaxed">
              <span className="text-slate-600 select-none text-[10px]">[{log.time}]</span>
              <span className={color}>{log.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
