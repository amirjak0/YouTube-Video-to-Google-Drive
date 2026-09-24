import React, { useState } from 'react';
import {
  HardDrive,
  Search,
  Trash2,
  ExternalLink,
  Filter,
  CheckCircle,
  FileVideo,
  Database,
  RefreshCw,
  Sparkles,
  ArrowUpRight
} from 'lucide-react';
import { DriveFileItem } from '../types';

interface DriveVaultProps {
  files: DriveFileItem[];
  isLoading: boolean;
  onDeleteFile: (fileId: string) => void;
  onRefresh: () => void;
  folderId: string;
  driveMode: string;
  token?: string | null;
}

export const DriveVault: React.FC<DriveVaultProps> = ({
  files,
  isLoading,
  onDeleteFile,
  onRefresh,
  folderId,
  driveMode,
  token
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [resolutionFilter, setResolutionFilter] = useState<string>('all');
  const [verificationData, setVerificationData] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleLiveVerification = async () => {
    setIsVerifying(true);
    try {
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch('/api/drive/verify', { headers });
      const data = await res.json();
      setVerificationData(data);
    } catch (err: any) {
      setVerificationData({
        authenticated: false,
        message: 'خطا در برقراری ارتباط با سرور: ' + err.message
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const filteredFiles = files.filter(f => {
    const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (f.videoId && f.videoId.toLowerCase().includes(searchQuery.toLowerCase()));
    
    if (!matchesSearch) return false;
    if (resolutionFilter === 'all') return true;
    if (resolutionFilter === '4k') return f.height >= 2160;
    if (resolutionFilter === '1080p') return f.height === 1080;
    if (resolutionFilter === '720p') return f.height === 720;
    return true;
  });

  const totalBytes = files.reduce((acc, f) => acc + (f.size || 0), 0);
  const totalGb = (totalBytes / (1024 * 1024 * 1024)).toFixed(2);
  const count4k = files.filter(f => f.height >= 2160).length;
  const count1080 = files.filter(f => f.height === 1080).length;
  const count720 = files.filter(f => f.height === 720).length;

  const formatSize = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-6">
      {/* Vault Header & Stats */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-bold text-white">Google Drive Synced Vault</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-300 border border-blue-500/20">
                Folder ID: {folderId}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Synchronized YouTube video library stored in your configured Google Drive folder.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleLiveVerification}
              disabled={isVerifying}
              className="text-xs px-3.5 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 transition flex items-center gap-1.5 shadow-sm"
            >
              <CheckCircle className={`w-3.5 h-3.5 text-emerald-400 ${isVerifying ? 'animate-spin' : ''}`} />
              <span>{isVerifying ? 'در حال استعلام از Google Drive...' : '🔍 راستی‌آزمایی رسمی از Google Drive'}</span>
            </button>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>بازخوانی پوشه</span>
            </button>
            <a
              href={folderId ? `https://drive.google.com/drive/folders/${folderId}` : 'https://drive.google.com/drive/my-drive'}
              target="_blank"
              rel="noreferrer"
              className="text-xs px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 transition flex items-center gap-1.5"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>مشاهده مستقیم در Google Drive ↗</span>
            </a>
          </div>
        </div>

        {/* Live Verification Report Card */}
        {verificationData && (
          <div className={`mt-5 p-4 rounded-xl border text-xs transition-all ${
            verificationData.authenticated
              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
              : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
          }`}>
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2 font-bold text-sm">
                  {verificationData.authenticated ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span>نتیجه راستی‌آزمایی Google Drive API: متصل و تأیید شد</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <span>نتیجه راستی‌آزمایی: نیاز به احراز هویت درایو</span>
                    </>
                  )}
                </div>
                <p className="text-slate-300 leading-relaxed">{verificationData.message}</p>
                {verificationData.folderUrl && (
                  <div className="pt-1">
                    <a
                      href={verificationData.folderUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-blue-400 hover:text-blue-300 underline"
                    >
                      <span>باز کردن پوشه اختصاصی شما در Google Drive</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )}
                {verificationData.files && verificationData.files.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-1">
                    <div className="font-semibold text-slate-200">فایل‌های ثبت‌شده و تاییدشده در Google Drive:</div>
                    <div className="space-y-1 font-mono text-[11px]">
                      {verificationData.files.map((vf: any) => (
                        <div key={vf.id} className="flex items-center justify-between p-1.5 rounded bg-slate-900/80 border border-slate-800">
                          <span className="text-slate-200 truncate max-w-md">{vf.name}</span>
                          <a
                            href={vf.webViewLink}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-400 hover:underline flex items-center gap-1 text-[10px]"
                          >
                            <span>لینک مستقیم درایو</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <button
                onClick={() => setVerificationData(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-slate-800/80">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total Videos</div>
            <div className="text-xl font-bold text-white mt-1 font-mono">{files.length}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Drive Space</div>
            <div className="text-xl font-bold text-blue-400 mt-1 font-mono">{totalGb} GB</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">4K UHD Files</div>
            <div className="text-xl font-bold text-amber-400 mt-1 font-mono">{count4k}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">1080p FHD</div>
            <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">{count1080}</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Drive files or video ID..."
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
          />
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-500 mr-1" />
          {['all', '4k', '1080p', '720p'].map((filt) => (
            <button
              key={filt}
              onClick={() => setResolutionFilter(filt)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                resolutionFilter === filt
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
              }`}
            >
              {filt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Files List Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-lg">
        {filteredFiles.length > 0 ? (
          <div className="divide-y divide-slate-800/60">
            {filteredFiles.map((file) => {
              const is4k = file.height >= 2160;
              const is1080 = file.height === 1080;

              return (
                <div
                  key={file.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-850/60 transition group"
                >
                  <div className="flex items-start sm:items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <FileVideo className="w-5 h-5 text-red-400" />
                    </div>

                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-sm font-medium text-slate-200 truncate group-hover:text-white transition">
                          {file.name}
                        </h4>

                        {/* Resolution Tag Badge */}
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                            is4k
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : is1080
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          }`}
                        >
                          {file.height}p {is4k ? '4K UHD' : ''}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                        {file.videoId && (
                          <span className="font-mono text-slate-400">
                            ID: {file.videoId}
                          </span>
                        )}
                        <span>•</span>
                        <span>{formatSize(file.size)}</span>
                        <span>•</span>
                        <span>Synced {new Date(file.createdTime).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                    {file.driveUrl && (
                      <a
                        href={file.driveUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 text-slate-400 hover:text-blue-300 hover:bg-blue-500/10 rounded-lg transition"
                        title="Open in Drive"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      onClick={() => onDeleteFile(file.id)}
                      className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                      title="Delete from Google Drive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 px-4">
            <HardDrive className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-400 font-medium">No files found matching your filter</p>
            <p className="text-xs text-slate-500 mt-1">
              Synchronize videos from the "Sync & Upgrade" tab to populate your Google Drive vault.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
