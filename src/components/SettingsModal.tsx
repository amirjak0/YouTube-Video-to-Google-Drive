import React, { useState, useEffect } from 'react';
import { X, Save, Sliders, Key, ShieldCheck, HardDrive, Check, Copy, ExternalLink, HelpCircle } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveConfig: (newConfig: any) => void;
  initialConfig: any;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSaveConfig,
  initialConfig
}) => {
  const [folderId, setFolderId] = useState(initialConfig?.gdriveFolderId || '');
  const [playlistUrl, setPlaylistUrl] = useState(initialConfig?.playlistUrl || '');
  const [updateExisting, setUpdateExisting] = useState(initialConfig?.updateExisting ?? true);
  const [forceRetry, setForceRetry] = useState(initialConfig?.forceRetry ?? false);
  const [maxResolution, setMaxResolution] = useState(initialConfig?.maxResolution || 2160);
  const [activeTab, setActiveTab] = useState<'sync' | 'secrets' | 'github'>('sync');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    if (initialConfig) {
      setFolderId(initialConfig.gdriveFolderId || '');
      setPlaylistUrl(initialConfig.playlistUrl || '');
      setUpdateExisting(initialConfig.updateExisting ?? true);
      setForceRetry(initialConfig.forceRetry ?? false);
      setMaxResolution(initialConfig.maxResolution || 2160);
    }
  }, [initialConfig]);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveConfig({
      gdriveFolderId: folderId,
      playlistUrl,
      updateExisting,
      forceRetry,
      maxResolution: Number(maxResolution)
    });
    onClose();
  };

  const copySecret = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(label);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-red-400" />
            <h3 className="text-base font-bold text-white">Synchronizer & Drive Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-800 bg-slate-950/60 px-5 text-xs font-medium">
          <button
            onClick={() => setActiveTab('sync')}
            className={`py-3 px-3 border-b-2 transition ${
              activeTab === 'sync'
                ? 'border-red-500 text-red-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Sync Rules & Resolution
          </button>
          <button
            onClick={() => setActiveTab('secrets')}
            className={`py-3 px-3 border-b-2 transition ${
              activeTab === 'secrets'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Drive Credentials Status
          </button>
          <button
            onClick={() => setActiveTab('github')}
            className={`py-3 px-3 border-b-2 transition ${
              activeTab === 'github'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            GitHub Actions Sync
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300 flex-1">
          {activeTab === 'sync' && (
            <>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Google Drive Target Folder ID
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={folderId}
                    onChange={(e) => setFolderId(e.target.value)}
                    placeholder="e.g. 1A2b3C4d5E6f_YouTubeVault"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-blue-500/80"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Found in the URL of your Google Drive folder: <code className="text-slate-400">drive.google.com/drive/folders/<strong>[FOLDER_ID]</strong></code>
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Default YouTube Playlist URL
                </label>
                <input
                  type="text"
                  value={playlistUrl}
                  onChange={(e) => setPlaylistUrl(e.target.value)}
                  placeholder="https://www.youtube.com/playlist?list=..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-100 text-xs focus:outline-none focus:border-red-500/80"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Maximum Resolution Cap
                  </label>
                  <select
                    value={maxResolution}
                    onChange={(e) => setMaxResolution(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-100 text-xs focus:outline-none focus:border-red-500/80"
                  >
                    <option value={2160}>2160p (4K UHD) - Maximum Quality</option>
                    <option value={1440}>1440p (2K QHD)</option>
                    <option value={1080}>1080p (Full HD 1080p)</option>
                    <option value={720}>720p (HD 720p)</option>
                  </select>
                </div>

                <div className="space-y-2 pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={updateExisting}
                      onChange={(e) => setUpdateExisting(e.target.checked)}
                      className="w-4 h-4 rounded text-red-600 focus:ring-0 bg-slate-950 border-slate-800"
                    />
                    <div>
                      <span className="font-semibold text-slate-200">Auto-Upgrade Existing Videos</span>
                      <p className="text-[11px] text-slate-500">
                        Replace lower-resolution Drive files (e.g. 720p) with newly available higher resolution (4K)
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                  <span>Probe Candidate Order</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  <code className="text-amber-300">tv</code> (4K) ➔ <code className="text-slate-300">web</code> ➔ <code className="text-slate-300">android</code> ➔ <code className="text-slate-300">ios</code> ➔ <code className="text-slate-300">tv_simply</code> ➔ <code className="text-slate-300">web_safari</code> ➔ <code className="text-slate-300">mweb</code>
                </p>
              </div>
            </>
          )}

          {activeTab === 'secrets' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                To connect your personal Google Drive for automated direct file uploads, configure the OAuth credentials below or provide them in your environment / GitHub repository secrets.
              </div>

              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-slate-200">GDRIVE_CLIENT_ID</div>
                    <div className="text-[11px] text-slate-500">Google Cloud OAuth 2.0 Client ID</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${initialConfig?.hasClientId ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                    {initialConfig?.hasClientId ? 'Configured' : 'Not Set (Using Vault)'}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-slate-200">GDRIVE_CLIENT_SECRET</div>
                    <div className="text-[11px] text-slate-500">Google Cloud OAuth 2.0 Client Secret</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${initialConfig?.hasClientSecret ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                    {initialConfig?.hasClientSecret ? 'Configured' : 'Not Set (Using Vault)'}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-slate-200">GDRIVE_REFRESH_TOKEN</div>
                    <div className="text-[11px] text-slate-500">Google OAuth Offline Refresh Token</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${initialConfig?.hasRefreshToken ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                    {initialConfig?.hasRefreshToken ? 'Configured' : 'Not Set (Using Vault)'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'github' && (
            <div className="space-y-4 text-right" dir="rtl">
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs leading-relaxed">
                <strong>راهنمای اجرای کاملاً خودکار هر ۶ ساعت یک‌بار (بدون نیاز به کامپیوتر یا اینترنت):</strong>
                <p className="mt-1 text-slate-300">
                  این پروژه در گیت‌هاب دارای فایلی به نام <code className="text-emerald-400 font-mono">.github/workflows/run.yml</code> است که هر ۶ ساعت روی سرورهای ابری گیت‌هاب اجرا می‌شود. برای فعال‌سازی آن نیازی به روشن بودن دستگاه شما نیست.
                </p>
              </div>

              <div className="space-y-2">
                <div className="font-semibold text-slate-200 text-xs">مراحل تنظیم در گیت‌هاب (فقط یک‌بار):</div>
                <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-slate-400 pr-1">
                  <li>به مخزن خود در GitHub بروید.</li>
                  <li>روی تب <strong className="text-slate-200">Settings</strong> کلیک کنید.</li>
                  <li>از منوی سمت چپ، بخش <strong className="text-slate-200">Secrets and variables</strong> و سپس <strong className="text-slate-200">Actions</strong> را باز کنید.</li>
                  <li>روی دکمه <strong className="text-slate-200">New repository secret</strong> کلیک کنید و متغیرهای زیر را وارد کنید:</li>
                </ol>
              </div>

              <div className="space-y-2 text-left" dir="ltr">
                {[
                  { key: 'YOUTUBE_PLAYLIST_URL', desc: 'لینک پلی‌لیست یوتیوب شما' },
                  { key: 'GDRIVE_FOLDER_ID', desc: 'شناسه پوشه مقصد در گوگل درایو' },
                  { key: 'GDRIVE_CLIENT_ID', desc: 'شناسه Google OAuth Client ID' },
                  { key: 'GDRIVE_CLIENT_SECRET', desc: 'رمز Google OAuth Client Secret' },
                  { key: 'GDRIVE_REFRESH_TOKEN', desc: 'توکن آفلاین رفرش درایو' },
                  { key: 'YOUTUBE_COOKIES', desc: 'کوکی‌های اختیاری یوتیوب جهت جلوگیری از بلاک' }
                ].map((item) => (
                  <div key={item.key} className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="font-mono text-xs text-amber-300 font-medium">{item.key}</div>
                      <div className="text-[10px] text-slate-500">{item.desc}</div>
                    </div>
                    <button
                      onClick={() => copySecret(item.key, item.key)}
                      className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1"
                    >
                      {copiedKey === item.key ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-[10px] text-emerald-400">کپی شد</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span className="text-[10px]">کپی</span>
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400">
                💡 <span className="text-slate-200 font-semibold">تست دستی:</span> در گیت‌هاب می‌توانید به تب <strong className="text-slate-200">Actions</strong> بروید، روی کار <strong className="text-slate-200">YouTube to Google Drive</strong> کلیک کنید و با دکمه <strong className="text-emerald-400">Run workflow</strong> تست فوری انجام دهید.
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-end gap-2 bg-slate-950/40">
          <button
            onClick={onClose}
            className="text-xs px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-xs px-5 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold shadow-lg shadow-red-500/20 transition flex items-center gap-1.5"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};
