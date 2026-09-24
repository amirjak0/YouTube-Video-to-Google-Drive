import React from 'react';
import { HardDrive, Video, RefreshCw, Settings, ShieldCheck, CloudOff, CheckCircle2, Sparkles } from 'lucide-react';
import { SystemStatus } from '../types';

interface HeaderProps {
  status: SystemStatus | null;
  onOpenSettings: () => void;
  activeTab: 'sync' | 'drive' | 'probe';
  setActiveTab: (tab: 'sync' | 'drive' | 'probe') => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  user?: any | null;
  onConnectDrive?: () => void;
  onDisconnectDrive?: () => void;
  isConnectingDrive?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  onOpenSettings,
  activeTab,
  setActiveTab,
  onRefresh,
  isRefreshing,
  user,
  onConnectDrive,
  onDisconnectDrive,
  isConnectingDrive
}) => {
  return (
    <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-red-600 to-amber-500 shadow-lg shadow-red-500/20 text-white">
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="text-slate-600 font-medium">➔</span>
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
                <HardDrive className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  YouTube <span className="text-red-400">→</span> Google Drive
                </h1>
                <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                  4K Auto-Sync
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Multi-Client Probe & Auto-Upgrade Engine
              </p>
            </div>
          </div>

          {/* Navigation tabs */}
          <nav className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('sync')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === 'sync'
                  ? 'bg-red-500/20 text-red-300 border border-red-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Sync & Upgrade</span>
            </button>
            <button
              onClick={() => setActiveTab('drive')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === 'drive'
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <HardDrive className="w-3.5 h-3.5" />
              <span>Drive Vault</span>
              {status && status.totalFilesTracked > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/30 text-blue-200">
                  {status.totalFilesTracked}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('probe')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === 'probe'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Client Probe</span>
              <span className="sm:hidden">Clients</span>
            </button>
          </nav>

          {/* Right utilities: Status & Settings */}
          <div className="flex items-center gap-2">
            {/* Google Drive Connect Button */}
            {user ? (
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs">
                {user.photoURL ? (
                  <img src={user.photoURL} alt="" className="w-5 h-5 rounded-full" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-emerald-600 text-[10px] flex items-center justify-center font-bold text-white">
                    {user.email ? user.email[0].toUpperCase() : 'G'}
                  </div>
                )}
                <span className="text-emerald-300 font-medium hidden sm:inline max-w-[120px] truncate">
                  {user.displayName || user.email}
                </span>
                <button
                  onClick={onDisconnectDrive}
                  title="قطع اتصال"
                  className="text-[10px] text-slate-400 hover:text-red-400 underline ml-1 cursor-pointer"
                >
                  خروج
                </button>
              </div>
            ) : (
              <button
                onClick={onConnectDrive}
                disabled={isConnectingDrive}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-medium text-xs shadow-md transition disabled:opacity-50 cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>{isConnectingDrive ? 'در حال اتصال...' : 'اتصال خودکار Google Drive'}</span>
              </button>
            )}

            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              <span>اجرای خودکار هر ۶ ساعت (ابری)</span>
            </div>

            <div className="hidden md:flex items-center gap-2 text-xs">
              {status?.driveConnected ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Drive API Connected</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                  <span>Vault Active</span>
                </div>
              )}
            </div>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh status & files"
              className="p-2 text-slate-400 hover:text-white rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-700/60 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-red-400' : ''}`} />
            </button>

            <button
              onClick={onOpenSettings}
              title="Configure Settings & Secrets"
              className="p-2 text-slate-400 hover:text-white rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-700/60 transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
