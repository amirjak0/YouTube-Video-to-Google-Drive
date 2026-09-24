import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import { initAuth, googleSignIn, logout } from './services/firebaseAuth';
import { Header } from './components/Header';
import { GoogleDriveAuth } from './components/GoogleDriveAuth';
import { SyncStudio } from './components/SyncStudio';
import { DriveVault } from './components/DriveVault';
import { ClientInspector } from './components/ClientInspector';
import { LiveJobDrawer } from './components/LiveJobDrawer';
import { SettingsModal } from './components/SettingsModal';
import { SystemStatus, DriveFileItem, VideoMetadata, SyncJob } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<'sync' | 'drive' | 'probe'>('sync');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [config, setConfig] = useState<any>(null);
  const [driveFiles, setDriveFiles] = useState<DriveFileItem[]>([]);
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [currentUrl, setCurrentUrl] = useState<string>('https://www.youtube.com/playlist?list=PLANLPlXI3s4o');
  const [probeError, setProbeError] = useState<string | null>(null);

  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isTokenExpired, setIsTokenExpired] = useState(false);
  const [isConnectingAuth, setIsConnectingAuth] = useState(false);

  const [isLoadingVideos, setIsLoadingVideos] = useState(false);
  const [isLoadingDrive, setIsLoadingDrive] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [activeJob, setActiveJob] = useState<SyncJob | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<DriveFileItem | null>(null);

  // Initialize Firebase Auth listener
  useEffect(() => {
    const unsubscribe = initAuth(
      (authUser, authToken) => {
        setUser(authUser);
        setToken(authToken);
        setIsTokenExpired(false);
        fetchDriveFiles(authToken);
      },
      () => {
        setUser(null);
        setToken(null);
        fetchDriveFiles(null);
      }
    );
    return () => unsubscribe();
  }, []);

  // Fetch system status
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err: any) {
      console.warn('Status fetch notice:', err?.message || err);
    }
  };

  // Fetch configuration
  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        if (data.playlistUrl && !currentUrl) {
          setCurrentUrl(data.playlistUrl);
        }
      }
    } catch (err: any) {
      console.warn('Config fetch notice:', err?.message || err);
    }
  };

  // Fetch drive files with token and auto-retry
  const fetchDriveFiles = async (authToken?: string | null, retriesLeft: number = 2) => {
    setIsLoadingDrive(true);
    try {
      const currentToken = authToken !== undefined ? authToken : token;
      const headers: Record<string, string> = {};
      if (currentToken) {
        headers['Authorization'] = `Bearer ${currentToken}`;
      }
      const res = await fetch('/api/drive/files', { headers });
      if (res.status === 401) {
        setToken(null);
        setIsTokenExpired(true);
        return;
      }
      if (res.ok) {
        setIsTokenExpired(false);
        const data = await res.json();
        setDriveFiles(data.files || []);
        if (data.folderId && (!config?.gdriveFolderId || config?.gdriveFolderId === '')) {
          setConfig((prev: any) => ({ ...prev, gdriveFolderId: data.folderId }));
        }
      }
    } catch (err: any) {
      if (retriesLeft > 0) {
        setTimeout(() => fetchDriveFiles(authToken, retriesLeft - 1), 1000);
      } else {
        console.warn('Drive files fetch notice (will retry upon next interaction):', err?.message || err);
      }
    } finally {
      setIsLoadingDrive(false);
    }
  };

  // Probe YouTube URL
  const handleProbe = async (url: string) => {
    if (!url || !url.trim()) return;
    setIsLoadingVideos(true);
    setProbeError(null);
    try {
      const res = await fetch('/api/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() })
      });
      const data = await res.json();
      if (res.ok && data.videos && data.videos.length > 0) {
        setVideos(data.videos);
        setProbeError(null);
      } else {
        setVideos([]);
        setProbeError(data.error || 'هیچ ویدیویی یافت نشد. لطفاً از عمومی (Public) بودن پلی‌لیست مطمئن شوید.');
      }
    } catch (err: any) {
      console.warn('Probe notice:', err?.message || err);
      setVideos([]);
      setProbeError('خطا در برقراری ارتباط با سرور: ' + err.message);
    } finally {
      setIsLoadingVideos(false);
    }
  };

  // Start Sync Job with Bearer token
  const handleStartSync = async (videoIds: string[], forceRetry: boolean = false) => {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch('/api/sync/start', {
        method: 'POST',
        headers,
        body: JSON.stringify({ videoIds, forceRetry })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveJob(data.job);
        setIsDrawerOpen(true);
      }
    } catch (err: any) {
      console.warn('Failed to start sync job:', err?.message || err);
    }
  };

  // Cancel Job
  const handleCancelJob = async (jobId: string) => {
    try {
      await fetch(`/api/sync/jobs/${jobId}/cancel`, { method: 'POST' });
    } catch (err: any) {
      console.warn('Failed to cancel job:', err?.message || err);
    }
  };

  // Request Delete file from Drive
  const handleDeleteDriveFile = (fileId: string) => {
    const fileItem = driveFiles.find(f => f.id === fileId);
    if (fileItem) {
      setFileToDelete(fileItem);
    }
  };

  // Confirm and execute delete
  const executeDeleteFile = async () => {
    if (!fileToDelete) return;
    const fileId = fileToDelete.id;
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch('/api/drive/files/delete', {
        method: 'POST',
        headers,
        body: JSON.stringify({ fileId })
      });
      if (res.ok) {
        setDriveFiles(prev => prev.filter(f => f.id !== fileId));
        fetchStatus();
      }
    } catch (err: any) {
      console.warn('Failed to delete file:', err?.message || err);
    } finally {
      setFileToDelete(null);
    }
  };

  // Save Settings
  const handleSaveConfig = async (newConfig: any) => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      if (res.ok) {
        fetchConfig();
        fetchStatus();
      }
    } catch (err) {
      console.error('Failed to update config:', err);
    }
  };

  // Refresh all
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([fetchStatus(), fetchConfig(), fetchDriveFiles(token)]);
    if (currentUrl) {
      await handleProbe(currentUrl);
    }
    setIsRefreshing(false);
  };

  // Initial load
  useEffect(() => {
    handleRefresh();
  }, []);

  // Poll active sync job if running
  useEffect(() => {
    if (!activeJob || activeJob.status !== 'running') return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/sync/jobs/${activeJob.id}`);
        if (res.ok) {
          const data = await res.json();
          setActiveJob(data.job);

          if (data.job.status === 'completed' || data.job.status === 'cancelled') {
            fetchDriveFiles(token);
            fetchStatus();
            if (currentUrl) handleProbe(currentUrl);
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeJob?.id, activeJob?.status, currentUrl, token]);

  const handleAuthChange = (newUser: User | null, newToken: string | null) => {
    setUser(newUser);
    setToken(newToken);
    setIsTokenExpired(!newToken && !!newUser);
    fetchDriveFiles(newToken);
  };

  const handleConnectDrive = async () => {
    setIsConnectingAuth(true);
    try {
      const res = await googleSignIn();
      if (res) {
        handleAuthChange(res.user, res.accessToken);
      }
    } catch (err) {
      console.warn('Connect drive notice:', err);
    } finally {
      setIsConnectingAuth(false);
    }
  };

  const handleDisconnectDrive = async () => {
    try {
      await logout();
      handleAuthChange(null, null);
    } catch (err) {
      console.warn('Disconnect drive notice:', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col" dir="rtl">
      <Header
        status={status}
        onOpenSettings={() => setIsSettingsOpen(true)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        user={token ? user : null}
        onConnectDrive={handleConnectDrive}
        onDisconnectDrive={handleDisconnectDrive}
        isConnectingDrive={isConnectingAuth}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-32 space-y-6">
        {/* Token Expired Notification Banner */}
        {isTokenExpired && (
          <div className="bg-amber-500/10 border border-amber-500/30 text-amber-300 px-4 py-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm shadow-lg backdrop-blur-sm">
            <div className="flex items-center gap-2.5">
              <span className="text-xl">⚠️</span>
              <span>نشست دسترسی به Google Drive منقضی شده است. برای فعال‌سازی مجدد استعلام و آپلود مستقیم، لطفاً مجدداً وارد حساب گوگل شوید.</span>
            </div>
            <button
              onClick={handleConnectDrive}
              disabled={isConnectingAuth}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl shadow-md transition disabled:opacity-50 shrink-0 cursor-pointer"
            >
              {isConnectingAuth ? 'در حال ورود...' : 'ورود و تمدید دسترسی گوگل'}
            </button>
          </div>
        )}

        {/* Google Drive Direct Connection Card */}
        <GoogleDriveAuth
          user={user}
          token={token}
          onAuthChange={handleAuthChange}
          folderId={config?.gdriveFolderId}
          onRefreshDrive={() => fetchDriveFiles(token)}
        />

        {activeTab === 'sync' && (
          <SyncStudio
            videos={videos}
            isLoadingVideos={isLoadingVideos}
            probeError={probeError}
            onProbe={handleProbe}
            onStartSync={handleStartSync}
            activeJob={activeJob}
            currentUrl={currentUrl}
            setCurrentUrl={setCurrentUrl}
          />
        )}

        {activeTab === 'drive' && (
          <DriveVault
            files={driveFiles}
            isLoading={isLoadingDrive}
            onDeleteFile={handleDeleteDriveFile}
            onRefresh={() => fetchDriveFiles(token)}
            folderId={status?.folderId || config?.gdriveFolderId || 'YouTube-AutoSync'}
            driveMode={user ? 'google_drive_connected' : (status?.driveMode || 'vault')}
            token={token}
          />
        )}

        {activeTab === 'probe' && <ClientInspector />}
      </main>

      {/* Floating active job pill when drawer is minimized */}
      {activeJob && !isDrawerOpen && (
        <div className="fixed bottom-5 left-5 z-30">
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="flex items-center gap-2.5 px-4 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl hover:border-blue-500/50 transition group"
          >
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                activeJob.status === 'running'
                  ? 'bg-amber-400 animate-pulse'
                  : 'bg-emerald-400'
              }`}
            />
            <span className="text-xs font-semibold text-slate-200">
              {activeJob.status === 'running'
                ? `در حال همگام‌سازی (${activeJob.processedVideos}/${activeJob.totalVideos})`
                : 'مشاهده گزارش آخرین همگام‌سازی'}
            </span>
            <span className="text-slate-500 group-hover:text-slate-300 text-xs">▲</span>
          </button>
        </div>
      )}

      {/* Live execution drawer */}
      <LiveJobDrawer
        job={activeJob}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onCancel={handleCancelJob}
      />

      {/* Delete Confirmation Modal */}
      {fileToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <span className="text-xl">⚠️</span>
              <h3 className="font-bold text-base text-slate-100">تأیید حذف فایل از درایو</h3>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              آیا از حذف دائمی فایل زیر اطمینان دارید؟
            </p>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 text-xs font-mono text-slate-300 break-all">
              {fileToDelete.name}
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setFileToDelete(null)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 rounded-xl transition"
              >
                انصراف
              </button>
              <button
                onClick={executeDeleteFile}
                className="px-4 py-2 text-xs font-medium text-white bg-red-600 hover:bg-red-500 rounded-xl shadow-lg shadow-red-600/20 transition"
              >
                بله، حذف شود
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaveConfig={handleSaveConfig}
        initialConfig={config}
      />
    </div>
  );
}
