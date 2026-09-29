import React, { useState, useEffect, useRef } from 'react';
import {
  Video,
  HardDrive,
  RefreshCw,
  Play,
  Square,
  Sparkles,
  ArrowUpRight,
  Terminal,
  Settings,
  Folder,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  Search,
  ExternalLink,
  ChevronRight,
  Cpu,
  ShieldCheck,
  FileVideo
} from 'lucide-react';

function YoutubeIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>
  );
}
import { VideoItem, DriveFile, LogEntry, SyncConfig, SyncStats } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<'queue' | 'drive' | 'logs' | 'settings'>('queue');
  const [config, setConfig] = useState<SyncConfig | null>(null);
  const [stats, setStats] = useState<SyncStats | null>(null);
  const [queue, setQueue] = useState<VideoItem[]>([]);
  const [driveFiles, setDriveFiles] = useState<DriveFile[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [quickUrl, setQuickUrl] = useState('');
  const [deleteConfirmFile, setDeleteConfirmFile] = useState<DriveFile | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Settings form state
  const [formYoutubeUrl, setFormYoutubeUrl] = useState('');
  const [formFolderId, setFormFolderId] = useState('');
  const [formUpdateExisting, setFormUpdateExisting] = useState(true);
  const [formQualityLimit, setFormQualityLimit] = useState(2160);
  const [formAutoSync, setFormAutoSync] = useState(true);
  const [formScheduleHours, setFormScheduleHours] = useState(6);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial data
  const fetchData = async () => {
    try {
      const [cfgRes, qRes, drvRes, logsRes] = await Promise.all([
        fetch('/api/config').then(r => r.json()),
        fetch('/api/sync/queue').then(r => r.json()),
        fetch('/api/drive/files').then(r => r.json()),
        fetch('/api/logs').then(r => r.json()),
      ]);

      if (cfgRes?.config) {
        setConfig(cfgRes.config);
        setStats(cfgRes.stats);
        if (!formYoutubeUrl) setFormYoutubeUrl(cfgRes.config.youtubeUrl);
        if (!formFolderId) setFormFolderId(cfgRes.config.targetFolderId);
        setFormUpdateExisting(cfgRes.config.updateExisting);
        setFormQualityLimit(cfgRes.config.forceQualityLimit);
        setFormAutoSync(cfgRes.config.autoSyncEnabled);
        setFormScheduleHours(cfgRes.config.scheduleIntervalHours);
      }
      if (qRes?.queue) setQueue(qRes.queue);
      if (drvRes?.files) setDriveFiles(drvRes.files);
      if (logsRes?.logs) setLogs(logsRes.logs);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2500);
    return () => clearInterval(interval);
  }, []);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setFeedbackMsg({ type, text });
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  const handleScan = async (overrideUrl?: string) => {
    setIsScanning(true);
    try {
      const res = await fetch('/api/sync/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: overrideUrl || quickUrl || config?.youtubeUrl,
          folderId: config?.targetFolderId,
        }),
      });
      const data = await res.json();
      if (data.queue) {
        setQueue(data.queue);
        showToast(`Scan complete: ${data.summary?.toSync || 0} new, ${data.summary?.toUpgrade || 0} upgrades available`);
      }
      if (overrideUrl) setQuickUrl('');
      fetchData();
    } catch (err) {
      showToast('Scan failed to complete', 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const handleStartSync = async (videoIds?: string[]) => {
    try {
      const res = await fetch('/api/sync/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoIds }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Sync started successfully!');
        fetchData();
      } else {
        showToast(data.error || 'Unable to start sync', 'error');
      }
    } catch {
      showToast('Failed to start sync', 'error');
    }
  };

  const handleStopSync = async () => {
    try {
      await fetch('/api/sync/stop', { method: 'POST' });
      showToast('Sync stop requested');
      fetchData();
    } catch {
      showToast('Error stopping sync', 'error');
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          youtubeUrl: formYoutubeUrl,
          targetFolderId: formFolderId,
          updateExisting: formUpdateExisting,
          forceQualityLimit: formQualityLimit,
          autoSyncEnabled: formAutoSync,
          scheduleIntervalHours: formScheduleHours,
        }),
      });
      if (res.ok) {
        showToast('Settings saved successfully');
        fetchData();
      }
    } catch {
      showToast('Failed to update settings', 'error');
    }
  };

  const handleDeleteDriveFile = async (id: string) => {
    try {
      const res = await fetch(`/api/drive/files/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('File removed from Google Drive storage');
        setDeleteConfirmFile(null);
        fetchData();
      }
    } catch {
      showToast('Failed to delete file', 'error');
    }
  };

  const handleClearLogs = async () => {
    try {
      await fetch('/api/logs/clear', { method: 'POST' });
      setLogs([]);
      showToast('Logs cleared');
    } catch {
      showToast('Failed to clear logs', 'error');
    }
  };

  const totalDriveSizeMb = driveFiles.reduce((acc, f) => acc + (f.size / (1024 * 1024)), 0);
  const eligibleUpgrades = queue.filter(q => q.driveStatus === 'upgrade_available');
  const pendingSync = queue.filter(q => q.driveStatus === 'not_synced');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Toast Notification */}
      {feedbackMsg && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl text-sm font-medium flex items-center gap-2 transition-all ${
          feedbackMsg.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {feedbackMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {feedbackMsg.text}
        </div>
      )}

      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-red-600 to-amber-500 flex items-center justify-center shadow-lg shadow-red-500/20">
              <YoutubeIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">YouTube to Google Drive</h1>
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Auto-Sync v2.1
                </span>
              </div>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <HardDrive className="w-3.5 h-3.5 text-blue-400" />
                Target Folder: <span className="font-mono text-slate-300">{config?.targetFolderId || 'Loading...'}</span>
              </p>
            </div>
          </div>

          {/* Sync Trigger / Progress Header Button */}
          <div className="flex items-center gap-2">
            {stats?.isRunning ? (
              <button
                onClick={handleStopSync}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-600/30 transition-colors"
              >
                <Square className="w-3.5 h-3.5" />
                Stop Syncing
              </button>
            ) : (
              <button
                onClick={() => handleStartSync()}
                disabled={isScanning}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white text-xs sm:text-sm font-semibold hover:bg-red-500 transition-all shadow-md shadow-red-600/30 disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-white" />
                Run Full Sync Now
              </button>
            )}

            <button
              onClick={() => handleScan()}
              disabled={isScanning || stats?.isRunning}
              title="Rescan YouTube Playlist and Drive Folder"
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin text-blue-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Global Progress Bar when syncing */}
        {stats?.isRunning && (
          <div className="w-full bg-slate-800/80 h-2 relative overflow-hidden border-t border-slate-800">
            <div
              className="bg-gradient-to-r from-red-600 via-amber-500 to-emerald-500 h-full transition-all duration-500 ease-out"
              style={{ width: `${Math.max(stats.progressPercent, 12)}%` }}
            />
          </div>
        )}
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* Active Sync Progress Banner */}
        {stats?.isRunning && (
          <div className="p-4 rounded-xl bg-slate-900 border border-red-500/30 flex items-center justify-between gap-4 shadow-lg shadow-red-950/20">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0">
                <RefreshCw className="w-5 h-5 text-red-400 animate-spin" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-red-400">Sync Engine In Progress</p>
                <p className="text-sm font-medium text-slate-200 truncate max-w-xl">
                  {stats.currentVideoTitle || 'Processing streams with multi-client format probing...'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-white">{stats.progressPercent}%</span>
              <p className="text-xs text-slate-400">Merged & Verified</p>
            </div>
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Drive Storage</span>
              <HardDrive className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-xl font-bold text-white">{totalDriveSizeMb.toFixed(0)} <span className="text-xs font-normal text-slate-400">MB</span></p>
            <p className="text-[11px] text-slate-400 mt-1">{driveFiles.length} videos stored</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Auto-Upgrades</span>
              <Sparkles className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xl font-bold text-amber-400">{stats?.totalUpgraded || 0}</p>
            <p className="text-[11px] text-slate-400 mt-1">Old low-res purged</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Pending Transfer</span>
              <Clock className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-xl font-bold text-emerald-400">{pendingSync.length + eligibleUpgrades.length}</p>
            <p className="text-[11px] text-slate-400 mt-1">{eligibleUpgrades.length} upgrades ready</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Engine Status</span>
              <ShieldCheck className="w-4 h-4 text-purple-400" />
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-sm font-semibold text-slate-200">
                {config?.hasDriveCredentials ? 'Cloud Direct' : 'Drive Local Mode'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Max: {config?.forceQualityLimit}p 4K</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto pb-px">
          <button
            onClick={() => setActiveTab('queue')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'queue'
                ? 'border-red-500 text-white bg-slate-900/40 rounded-t-lg'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            Video Sync Queue
            {eligibleUpgrades.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500 text-slate-950">
                {eligibleUpgrades.length} upgrade
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('drive')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'drive'
                ? 'border-blue-500 text-white bg-slate-900/40 rounded-t-lg'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Folder className="w-4 h-4" />
            Google Drive Files ({driveFiles.length})
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'logs'
                ? 'border-emerald-500 text-white bg-slate-900/40 rounded-t-lg'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" />
            Execution Console
            {logs.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300">
                {logs.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'settings'
                ? 'border-purple-500 text-white bg-slate-900/40 rounded-t-lg'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Settings className="w-4 h-4" />
            Automation Settings
          </button>
        </div>

        {/* TAB 1: Video Sync Queue */}
        {activeTab === 'queue' && (
          <div className="space-y-4">
            {/* Quick URL Adder / Scanner Bar */}
            <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 flex flex-wrap sm:flex-nowrap items-center gap-2">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Paste YouTube Video or Playlist URL to probe..."
                  value={quickUrl}
                  onChange={(e) => setQuickUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleScan(quickUrl)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500"
                />
              </div>
              <button
                onClick={() => handleScan(quickUrl)}
                disabled={isScanning}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm font-medium text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <Cpu className="w-4 h-4 text-amber-400" />
                {isScanning ? 'Probing...' : 'Probe & Add'}
              </button>
              {(pendingSync.length > 0 || eligibleUpgrades.length > 0) && (
                <button
                  onClick={() => handleStartSync()}
                  disabled={stats?.isRunning}
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-xs sm:text-sm font-semibold text-white flex items-center gap-1.5 transition-colors"
                >
                  <Play className="w-3.5 h-3.5 fill-white" />
                  Sync All ({pendingSync.length + eligibleUpgrades.length})
                </button>
              )}
            </div>

            {/* Video Queue Table / Card List */}
            <div className="bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Detected Playlist Videos</h3>
                  <p className="text-xs text-slate-400">Multi-client probed formats compared against Google Drive folder state</p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="flex items-center gap-1 text-emerald-400">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Synced
                  </span>
                  <span className="flex items-center gap-1 text-amber-400">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span> Upgrade Ready
                  </span>
                  <span className="flex items-center gap-1 text-slate-400">
                    <span className="w-2 h-2 rounded-full bg-slate-500"></span> Not in Drive
                  </span>
                </div>
              </div>

              <div className="divide-y divide-slate-800/80">
                {queue.map((video) => (
                  <div key={video.id} className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-start gap-3.5 flex-1 min-w-0">
                      <div className="relative w-24 h-16 rounded-lg overflow-hidden bg-slate-800 shrink-0 border border-slate-700/50">
                        <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" />
                        <span className="absolute bottom-1 right-1 px-1 py-0.2 rounded text-[10px] font-mono bg-black/80 text-white">
                          {video.duration}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-medium text-white truncate max-w-md">{video.title}</h4>
                          <a
                            href={video.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-red-400 transition-colors"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-slate-400">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                            ID: [{video.id}]
                          </span>
                          <span className="px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/40 text-[11px]">
                            Available: {video.availableResolution}p
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                            Client: {video.chosenClient}
                          </span>
                          <span className="text-slate-500">~{video.fileSizeMb} MB</span>
                        </div>
                      </div>
                    </div>

                    {/* Sync Status Badge & Action */}
                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      {video.driveStatus === 'synced' && (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Max Quality ({video.availableResolution}p)</span>
                        </div>
                      )}

                      {video.driveStatus === 'upgrade_available' && (
                        <div className="flex flex-col sm:items-end gap-1">
                          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
                            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                            <span>Upgrade: {video.existingDriveResolution}p → {video.availableResolution}p</span>
                          </div>
                          <button
                            onClick={() => handleStartSync([video.id])}
                            disabled={stats?.isRunning}
                            className="text-[11px] font-semibold text-amber-400 hover:underline flex items-center gap-1"
                          >
                            Upgrade & Purge Old <ArrowUpRight className="w-3 h-3" />
                          </button>
                        </div>
                      )}

                      {video.driveStatus === 'not_synced' && (
                        <button
                          onClick={() => handleStartSync([video.id])}
                          disabled={stats?.isRunning}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
                        >
                          <Play className="w-3 h-3 fill-slate-200" />
                          Sync to Drive
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Google Drive Explorer */}
        {activeTab === 'drive' && (
          <div className="space-y-4">
            <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-blue-400" />
                  Google Drive Folder Storage
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Synchronized video files formatted with resolution tags: <code className="text-slate-300 font-mono">Title [VideoID] [Heightp].mkv</code>
                </p>
              </div>
              <div className="text-right text-xs">
                <span className="font-semibold text-white">{driveFiles.length} files</span>
                <p className="text-slate-400">{totalDriveSizeMb.toFixed(1)} MB total</p>
              </div>
            </div>

            <div className="bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden divide-y divide-slate-800">
              {driveFiles.length === 0 ? (
                <div className="p-12 text-center text-slate-400">
                  <Folder className="w-10 h-10 mx-auto text-slate-600 mb-2" />
                  <p className="text-sm">No files uploaded to Google Drive folder yet.</p>
                  <button
                    onClick={() => handleStartSync()}
                    className="mt-3 px-4 py-1.5 rounded-lg bg-red-600 text-white text-xs font-semibold hover:bg-red-500"
                  >
                    Run Sync Now
                  </button>
                </div>
              ) : (
                driveFiles.map((file) => (
                  <div key={file.id} className="p-4 flex items-center justify-between gap-4 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
                        <FileVideo className="w-5 h-5 text-blue-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-200 truncate">{file.name}</p>
                        <div className="flex items-center gap-2.5 text-xs text-slate-400 mt-1">
                          <span className="px-2 py-0.5 rounded bg-blue-900/40 text-blue-300 font-mono text-[11px] font-semibold border border-blue-800/40">
                            {file.resolution}p HD
                          </span>
                          <span>{(file.size / (1024 * 1024)).toFixed(1)} MB</span>
                          <span className="text-slate-500">Synced: {new Date(file.createdTime).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {file.webViewLink && (
                        <a
                          href={file.webViewLink}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                          title="View on Google Drive"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}
                      <button
                        onClick={() => setDeleteConfirmFile(file)}
                        className="p-2 rounded-lg bg-slate-800 hover:bg-red-900/40 text-slate-400 hover:text-red-400 transition-colors"
                        title="Delete from Google Drive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 3: Execution Console & Logs */}
        {activeTab === 'logs' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  Live Sync Engine Console
                </h3>
                <p className="text-xs text-slate-400">Replicating Python yt-gdrive-sync multi-client stdout stream</p>
              </div>
              <button
                onClick={handleClearLogs}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition-colors"
              >
                Clear Console
              </button>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs overflow-y-auto max-h-[500px] space-y-1.5 shadow-inner">
              {logs.length === 0 ? (
                <p className="text-slate-500 italic">No logs recorded yet.</p>
              ) : (
                logs.map((log) => {
                  let badgeColor = 'text-blue-400';
                  if (log.level === 'SUCCESS') badgeColor = 'text-emerald-400 font-bold';
                  if (log.level === 'WARNING') badgeColor = 'text-amber-400';
                  if (log.level === 'ERROR') badgeColor = 'text-red-400 font-bold';

                  return (
                    <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                      <span className="text-slate-500 shrink-0">[{log.timestamp}]</span>
                      <span className={`shrink-0 ${badgeColor}`}>{log.level}:</span>
                      <span className="text-slate-300 break-words">{log.message}</span>
                    </div>
                  );
                })
              )}
              <div ref={terminalEndRef} />
            </div>
          </div>
        )}

        {/* TAB 4: Automation Settings */}
        {activeTab === 'settings' && (
          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 max-w-3xl">
            <h3 className="text-base font-semibold text-white mb-1">Synchronizer & Environment Settings</h3>
            <p className="text-xs text-slate-400 mb-6">
              Configure target playlist, Google Drive credentials, quality caps, and automatic schedule.
            </p>

            <form onSubmit={handleSaveSettings} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  YouTube Playlist or Video URL
                </label>
                <input
                  type="text"
                  value={formYoutubeUrl}
                  onChange={(e) => setFormYoutubeUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500 font-mono"
                  placeholder="https://www.youtube.com/playlist?list=..."
                  required
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Supports playlists (`list=...`) or individual video URLs (`v=...`).
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Target Google Drive Folder ID
                  </label>
                  <input
                    type="text"
                    value={formFolderId}
                    onChange={(e) => setFormFolderId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                    placeholder="1A2b3C4d5E_DriveFolderSync"
                    required
                  />
                  <p className="text-[11px] text-slate-400 mt-1">ID found in the Google Drive folder URL.</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Target Maximum Quality Limit
                  </label>
                  <select
                    value={formQualityLimit}
                    onChange={(e) => setFormQualityLimit(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value={2160}>2160p (4K Ultra HD)</option>
                    <option value={1440}>1440p (2K Quad HD)</option>
                    <option value={1080}>1080p (Full HD - Recommended)</option>
                    <option value={720}>720p (Standard HD)</option>
                    <option value={480}>480p (SD)</option>
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">Multi-client formats above this limit will be capped.</p>
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3 pt-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formUpdateExisting}
                    onChange={(e) => setFormUpdateExisting(e.target.checked)}
                    className="w-4 h-4 rounded text-red-600 bg-slate-950 border-slate-700 focus:ring-0"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-200">Auto-Upgrade Existing Videos</span>
                    <p className="text-xs text-slate-400">
                      If video already exists in Drive at 360p or 720p, download 1080p+ when available, upload, and purge the old lower-res copy.
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formAutoSync}
                    onChange={(e) => setFormAutoSync(e.target.checked)}
                    className="w-4 h-4 rounded text-red-600 bg-slate-950 border-slate-700 focus:ring-0"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-200">Automated Background Schedule</span>
                    <p className="text-xs text-slate-400">
                      Run automated sync interval every {formScheduleHours} hours (matching GitHub Action cron schedule).
                    </p>
                  </div>
                </label>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-400">Configuration persisted in-memory & environment</span>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs sm:text-sm font-semibold transition-colors"
                >
                  Save Configuration
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      {/* Delete Confirmation Modal (Workspace Guidelines: Mandatory User Confirmation for destructive actions) */}
      {deleteConfirmFile && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-3">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-semibold text-white">Confirm File Deletion</h3>
            </div>
            <p className="text-sm text-slate-300 mb-2">
              Are you sure you want to permanently delete this video from Google Drive?
            </p>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 break-words mb-5">
              {deleteConfirmFile.name}
            </div>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteConfirmFile(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm font-medium text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteDriveFile(deleteConfirmFile.id)}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-xs sm:text-sm font-semibold text-white transition-colors"
              >
                Delete File
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/40 py-3 text-center text-xs text-slate-400">
        <p>YouTube Video to Google Drive Sync • Ported to Web (Node.js 22 Runtime) • AI Studio</p>
      </footer>
    </div>
  );
}
