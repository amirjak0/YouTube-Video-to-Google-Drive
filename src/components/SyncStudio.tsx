import React, { useState } from 'react';
import {
  Play,
  Search,
  ArrowUpCircle,
  CheckCircle2,
  PlusCircle,
  Film,
  Sparkles,
  Layers,
  AlertCircle,
  Sliders,
  Tv,
  Check,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import { VideoMetadata, SyncJob } from '../types';

interface SyncStudioProps {
  videos: VideoMetadata[];
  isLoadingVideos: boolean;
  probeError?: string | null;
  onProbe: (url: string) => void;
  onStartSync: (videoIds: string[], forceRetry?: boolean) => void;
  activeJob: SyncJob | null;
  currentUrl: string;
  setCurrentUrl: (url: string) => void;
}

export const SyncStudio: React.FC<SyncStudioProps> = ({
  videos,
  isLoadingVideos,
  probeError,
  onProbe,
  onStartSync,
  activeJob,
  currentUrl,
  setCurrentUrl
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [inputMode, setInputMode] = useState<'playlist' | 'multi'>('playlist');

  const handleSelectAll = () => {
    if (selectedIds.length === videos.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(videos.map(v => v.id));
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleSelectNeedingAction = () => {
    const actionIds = videos
      .filter(v => v.driveStatus === 'upgrade_available' || v.driveStatus === 'missing')
      .map(v => v.id);
    setSelectedIds(actionIds);
  };

  const needsUpgradeCount = videos.filter(v => v.driveStatus === 'upgrade_available').length;
  const missingCount = videos.filter(v => v.driveStatus === 'missing').length;
  const upToDateCount = videos.filter(v => v.driveStatus === 'synced_current').length;

  return (
    <div className="space-y-6">
      {/* Top Search & URL Input Bar */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-60 h-60 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-60 h-60 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                <span>ورود آدرس پلی‌لیست اختصاصی شما (YouTube Playlist)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                لینک پلی‌لیست واقعی خودتان در یوتیوب را اینجا وارد کنید تا ویدیوهای دقیق آن واکشی شوند.
              </p>
            </div>

            {/* Input mode switcher */}
            <div className="flex items-center gap-1.5 p-1 bg-slate-950 border border-slate-800 rounded-xl text-xs">
              <button
                type="button"
                onClick={() => setInputMode('playlist')}
                className={`px-3 py-1 rounded-lg transition ${inputMode === 'playlist' ? 'bg-red-500/20 text-red-300 font-medium border border-red-500/30' : 'text-slate-400 hover:text-slate-200'}`}
              >
                لینک پلی‌لیست
              </button>
              <button
                type="button"
                onClick={() => setInputMode('multi')}
                className={`px-3 py-1 rounded-lg transition ${inputMode === 'multi' ? 'bg-red-500/20 text-red-300 font-medium border border-red-500/30' : 'text-slate-400 hover:text-slate-200'}`}
              >
                چندین لینک ویدیو
              </button>
            </div>
          </div>

          {/* URL Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (currentUrl.trim()) onProbe(currentUrl.trim());
            }}
            className="space-y-3"
          >
            {inputMode === 'playlist' ? (
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={currentUrl}
                  onChange={(e) => setCurrentUrl(e.target.value)}
                  placeholder="مثال: https://www.youtube.com/playlist?list=PL..."
                  dir="ltr"
                  className="w-full bg-slate-950 border border-slate-700/80 rounded-xl pl-10 pr-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500/50 transition font-mono"
                />
              </div>
            ) : (
              <div>
                <textarea
                  rows={3}
                  value={currentUrl}
                  onChange={(e) => setCurrentUrl(e.target.value)}
                  placeholder="لینک ویدیوها را خط به خط یا با کاما جدا کنید:&#10;https://www.youtube.com/watch?v=...&#10;https://www.youtube.com/watch?v=..."
                  dir="ltr"
                  className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500/50 transition font-mono"
                />
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="text-xs text-slate-400">
                💡 <span className="text-slate-300">نکته:</span> پلی‌لیست باید روی وضعیت <strong className="text-amber-300">Public</strong> (عمومی) باشد تا یوتیوب اجازه خواندن عناوین و ویدیوها را بدهد.
              </div>

              <button
                type="submit"
                disabled={isLoadingVideos || !currentUrl.trim()}
                className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-red-500/20 flex items-center justify-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isLoadingVideos ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>در حال استخراج ویدیوهای واقعی پلی‌لیست شما...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>بررسی و دریافت ویدیوهای پلی‌لیست من</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Probe Error notification if any */}
          {probeError && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-start gap-2.5 mt-3">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">عدم دسترسی به ویدیوها:</span> {probeError}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Summary Metrics & Actions Bar */}
      {videos.length > 0 && (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="font-semibold text-slate-300">Playlist Status:</span>

            {needsUpgradeCount > 0 && (
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
                <ArrowUpCircle className="w-3.5 h-3.5" />
                <span>{needsUpgradeCount} Ready for 4K/HD Upgrade</span>
              </div>
            )}

            {missingCount > 0 && (
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-medium">
                <PlusCircle className="w-3.5 h-3.5" />
                <span>{missingCount} Missing from Drive</span>
              </div>
            )}

            {upToDateCount > 0 && (
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{upToDateCount} Already at Max Quality</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectNeedingAction}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              Select Pending ({needsUpgradeCount + missingCount})
            </button>
            <button
              onClick={handleSelectAll}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              {selectedIds.length === videos.length ? 'Deselect All' : 'Select All'}
            </button>
            <button
              onClick={() => onStartSync(selectedIds.length > 0 ? selectedIds : videos.map(v => v.id), false)}
              disabled={activeJob?.status === 'running'}
              className="px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-medium text-xs rounded-xl shadow-lg shadow-emerald-500/20 flex items-center gap-2 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>
                {selectedIds.length > 0
                  ? `همگام‌سازی فایل‌های انتخابی (${selectedIds.length})`
                  : `همگام‌سازی هوشمند همه (${videos.length})`}
              </span>
            </button>
            <button
              onClick={() => onStartSync(selectedIds.length > 0 ? selectedIds : videos.map(v => v.id), true)}
              disabled={activeJob?.status === 'running'}
              title="نادیده گرفتن فایل‌های قبلی و شروع مجدد کامل دانلود و آپلود به درایو"
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium text-xs rounded-xl shadow-sm flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
              <span>⚡ همگام‌سازی اجباری مجدد (Force Re-Sync)</span>
            </button>
          </div>
        </div>
      )}

      {/* Video Cards Grid */}
      {videos.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {videos.map((video) => {
            const isSelected = selectedIds.includes(video.id);

            return (
              <div
                key={video.id}
                onClick={() => toggleSelect(video.id)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer relative group flex flex-col justify-between ${
                  isSelected
                    ? 'bg-slate-900 border-red-500/60 shadow-lg shadow-red-500/5 ring-1 ring-red-500/30'
                    : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div>
                  {/* Top Thumbnail & Info */}
                  <div className="flex gap-3">
                    <div className="relative w-32 h-20 rounded-xl overflow-hidden bg-slate-950 shrink-0 border border-slate-800">
                      <img
                        src={video.thumbnail}
                        alt={video.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-mono text-slate-200">
                        {video.duration || 'HD'}
                      </div>
                      <div className="absolute top-1 left-1">
                        <div
                          className={`w-4 h-4 rounded border flex items-center justify-center ${
                            isSelected
                              ? 'bg-red-500 border-red-400 text-white'
                              : 'bg-black/60 border-white/30'
                          }`}
                        >
                          {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[11px] font-mono text-slate-500 tracking-wider">
                          [{video.id}]
                        </span>
                        {/* Status Badge */}
                        {video.driveStatus === 'upgrade_available' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1 shrink-0">
                            <ArrowUpCircle className="w-3 h-3" />
                            <span>Upgrade to {video.bestHeight}p</span>
                          </span>
                        )}
                        {video.driveStatus === 'missing' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1 shrink-0">
                            <PlusCircle className="w-3 h-3" />
                            <span>Not in Drive</span>
                          </span>
                        )}
                        {video.driveStatus === 'synced_current' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 shrink-0">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Max ({video.bestHeight}p)</span>
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-semibold text-slate-200 line-clamp-2 mt-1 leading-snug">
                        {video.title}
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5 truncate">{video.author}</p>
                    </div>
                  </div>

                  {/* Multi-client detection breakdown */}
                  <div className="mt-3 pt-3 border-t border-slate-800/80">
                    <div className="flex items-center justify-between text-[11px] mb-1.5">
                      <span className="text-slate-400 flex items-center gap-1">
                        <Tv className="w-3 h-3 text-slate-500" />
                        <span>Client Probe:</span>
                        <strong className="text-slate-200 font-mono">
                          {video.bestClient.toUpperCase()}
                        </strong>
                      </span>
                      <span className="text-slate-300">
                        Online Max:{' '}
                        <span className="text-red-400 font-bold font-mono">
                          {video.bestHeight}p {video.bestHeight >= 2160 ? '(4K UHD)' : ''}
                        </span>
                      </span>
                    </div>

                    {/* Quality Comparison pill */}
                    <div className="flex items-center justify-between text-[11px] p-2 rounded-lg bg-slate-950/80 border border-slate-800">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">Google Drive:</span>
                        {video.currentDriveHeight ? (
                          <span className="font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                            {video.currentDriveHeight}p
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[10px]">None</span>
                        )}
                      </div>

                      <span className="text-slate-600">➔</span>

                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">Target Drive File:</span>
                        <span className="font-mono text-emerald-400 font-medium text-[10px]">
                          [{video.bestHeight}p].mkv
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card footer buttons */}
                <div className="mt-3 flex items-center justify-between gap-2 pt-2">
                  <a
                    href={video.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-[11px] text-slate-500 hover:text-slate-300 transition"
                  >
                    View on YouTube ↗
                  </a>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onStartSync([video.id]);
                    }}
                    disabled={activeJob?.status === 'running'}
                    className="text-xs px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium border border-slate-700/80 transition flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    <span>Sync This Video</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16 px-4 rounded-2xl bg-slate-900/40 border border-slate-800/80">
          <Film className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">هنوز ویدیویی بارگذاری نشده است</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4 leading-relaxed">
            لطفاً لینک پلی‌لیست واقعی خودتان در یوتیوب یا لینک ویدیوها را در کادر بالا وارد کرده و دکمه «بررسی و دریافت ویدیوهای پلی‌لیست من» را بزنید تا ویدیوهای شما نمایش داده شوند.
          </p>
        </div>
      )}
    </div>
  );
};
