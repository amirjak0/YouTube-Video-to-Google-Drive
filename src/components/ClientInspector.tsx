import React from 'react';
import { Tv, Globe, Smartphone, Monitor, ShieldAlert, Cpu, CheckCircle2 } from 'lucide-react';

export const ClientInspector: React.FC = () => {
  const clients = [
    {
      id: 'tv',
      name: 'YouTube on TV (Cobalt / Smart TV)',
      icon: Tv,
      maxRes: '2160p (4K UHD)',
      isPrimary: true,
      description: 'First priority candidate in main.py probe sequence. YouTube provides up to 4K VP9/AV01 streams for TV clients without bot-check throttling.',
      badgeColor: 'text-amber-400 bg-amber-400/10 border-amber-400/20'
    },
    {
      id: 'tv_simply',
      name: 'YouTube TV (Embedded / Lite)',
      icon: Tv,
      maxRes: '1440p / 2160p',
      isPrimary: false,
      description: 'Secondary TV profile candidate, helpful when Cobalt challenge occurs or fallback stream is needed.',
      badgeColor: 'text-blue-400 bg-blue-400/10 border-blue-400/20'
    },
    {
      id: 'web',
      name: 'Desktop Web Browser',
      icon: Globe,
      maxRes: '1080p / 1440p',
      isPrimary: false,
      description: 'Standard desktop client. Uses cookies and node yt-dlp-ejs runtime to solve JavaScript player challenges and SABR restrictions.',
      badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    },
    {
      id: 'android',
      name: 'Android Native Client',
      icon: Smartphone,
      maxRes: '1080p FHD',
      isPrimary: false,
      description: 'High reliability client candidate for audio and video streams with stable CDN endpoints and fallback resilience.',
      badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    },
    {
      id: 'ios',
      name: 'iOS Mobile Client',
      icon: Smartphone,
      maxRes: '1080p FHD',
      isPrimary: false,
      description: 'Clean HLS/MP4 streams with low throttling rates. Default fallback candidate when cookies are absent.',
      badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    },
    {
      id: 'web_safari',
      name: 'Safari Desktop / WebKit',
      icon: Monitor,
      maxRes: '1080p FHD',
      isPrimary: false,
      description: 'Alternative web client simulating Apple Safari user agent with standard MP4 AVC/AAC formats.',
      badgeColor: 'text-blue-400 bg-blue-400/10 border-blue-400/20'
    },
    {
      id: 'mweb',
      name: 'Mobile Web Browser',
      icon: Globe,
      maxRes: '720p HD',
      isPrimary: false,
      description: 'Lightweight low-bandwidth fallback when high-resolution formats are rate-limited or blocked.',
      badgeColor: 'text-slate-400 bg-slate-400/10 border-slate-400/20'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-red-400" />
          <span>Multi-Client Format Probing Architecture</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1 max-w-3xl">
          Unlike ordinary downloaders that query only standard web endpoints, this synchronizer probes multiple YouTube Player Clients in a prioritized sequence.
          This overcomes resolution caps (e.g. 360p/720p bot locks) and unblocks genuine 1080p and 4K (2160p) video streams before merging with FFmpeg.
        </p>

        {/* Priority Flow Diagram */}
        <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Probe Priority Sequence (main.py)
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {clients.map((c, i) => (
              <React.Fragment key={c.id}>
                <span className={`px-2.5 py-1 rounded-lg border font-mono font-medium ${c.badgeColor}`}>
                  {c.id}
                </span>
                {i < clients.length - 1 && <span className="text-slate-600 font-bold">➔</span>}
              </React.Fragment>
            ))}
          </div>
          <div className="mt-3 text-[11px] text-amber-400/90 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Probe stops immediately once 4K (2160p) format is discovered to prevent extra requests.</span>
          </div>
        </div>
      </div>

      {/* Client Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {clients.map((c) => {
          const Icon = c.icon;
          return (
            <div
              key={c.id}
              className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-300">
                    <Icon className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{c.name}</h3>
                    <span className="text-[11px] font-mono text-slate-500">client_id: {c.id}</span>
                  </div>
                </div>

                <span className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold border ${c.badgeColor}`}>
                  {c.maxRes}
                </span>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                {c.description}
              </p>

              {c.isPrimary && (
                <div className="text-[10px] uppercase tracking-wider font-semibold text-amber-400 bg-amber-400/10 px-2 py-1 rounded border border-amber-400/20 inline-block">
                  ★ 4K Discovery Priority
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
